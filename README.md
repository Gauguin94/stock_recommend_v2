
# EV Multi‑Agent Report Generator
**글로벌 전기차 상장사 9개**를 대상으로, **숫자(차트·기초 재무)**와 **최신 웹 자료(공시/IR/보도자료)**를 자동 수집·분석하여 **투자 관점 리포트**를 생성하는 에이전트를 설계하고 구현

## Overview

- **Objective** : 각 티커에 대해 **정량 점수(QuantScore)**와 **사업 전개 근거**를 수집·정리하여, SUMMARY / COMPANIES / REFERENCE (+ APPENDIX) 구조의 **Markdown 리포트** 자동 생성
- **Method** : AI Agent + **LangGraph 병렬 오케스트레이션** + **웹서치(2025 선호, 2024 허용)** + 간단 평가/보강(자율 보강 1회)
- **Tools** : LangGraph, LangChain(Core), FinanceDataReader, Tavily, BeautifulSoup4, pandas, numpy

## Features

- 웹 자료(IR/보도자료/SEC 등) 기반 **근거 문장 추출** 및 날짜·출처 자동 표기
- **가격·거래(OHLCV) + Finviz 스냅샷**으로 **QuantScore(0–100)** 산출
- **회사별 카드**(점수·시그널·근거 개수) 생성 및 **Markdown 보고서** 출력
- 최신성 정책: **2025 자료 우선**, **2024 허용**, 2023/2022 위주면 **자동 재검색** 1회

## Tech Stack 

| Category   | Details                                              |
|------------|------------------------------------------------------|
| Framework  | LangGraph, LangChain(Core), Python                   |
| Data       | FinanceDataReader(OHLCV), Finviz 스냅샷(내장 크롤러) |
| Search     | Tavily(Web), BeautifulSoup4                          |
| LLM        | (Optional, 주입식) – APPENDIX 고지/대체 파이프라인   |
| Orchestration | **Parallel branches + Quality Gate** (LangGraph)  |

## Agents
- **quant_analysis_agent** (`agents/quant_scorer_module.py`) : OHLCV + Finviz 스냅샷으로 **QuantScore** 산출(Trend/Momentum/Liquidity/Risk/Fund) 및 시그널 생성
- **filing_reader_agent** (`agents/filing_websearch_module.py`) : Tavily 웹서치로 “무슨 사업을 전개 중인가” **근거 문장(3–6개)** 수집(부족 시 1회 보강)
- **report_writer_agent** (`agents/report_writer_module.py`) : SUMMARY / COMPANIES / REFERENCE (+ APPENDIX) **Markdown** 리포트 생성

## Architecture (Mermaid)
```mermaid
flowchart TD
  IN([Input: 9 Tickers + Prices(OHLCV) + (Finviz optional)])
  SUP((supervisor_node))
  QA[quant_node<br/>(OHLCV+Finviz → QuantScore)]
  FR[filings_node<br/>(Web Search → Evidence)]
  GT{{quality_gate<br/>pass or refine?}}
  MG[[merge_node<br/>(회사별 카드 요약)]]
  RW[report_node<br/>(Markdown Report)]
  OUT([out/ev_report.md])

  IN --> SUP
  SUP --> QA
  SUP --> FR
  QA --> GT
  FR --> GT
  GT -- "refine (≤1)" --> FR
  GT -- "pass" --> MG
  MG --> RW
  RW --> OUT
```

---

## State (Canonical)

### 1) 최상위 스키마
```python
from typing import TypedDict, List, Dict, Optional, Any

class EVState(TypedDict, total=False):
    # 입력/공유 (읽기 전용)
    input: Dict[str, Any]        # {"companies":[{"ticker":str, "name":Optional[str]}, ...]}
    shared: Dict[str, Any]       # {"prices":{ticker:OHLCV_df}, "finviz":?, "filings_index":?, "llm":?, "report_path":str}

    # 에이전트 산출
    quant: Dict[str, Any]        # ticker -> QuantItem
    filings: Dict[str, Any]      # ticker -> FilingItem
    merged: Dict[str, Any]       # {"company_cards":[CompanyCard, ...]}
    report: Dict[str, Any]       # {"md_path":"out/ev_report.md", "artifacts":[]}

    # 운영
    eval_flags: Dict[str, Dict[str, str]]  # {"TSLA":{"business":"pass|refine"}}
    logs: List[Dict[str, Any]]             # [{"step":"...", "ticker":"...", ...}]
```

### 2) 하위 타입(의미)
```python
class QuantItem(TypedDict, total=False):
    score_0_100: int                     # 최종 정량 점수(높을수록 좋음, 0~100)
    blocks: Dict[str, float]             # {"fund":0~1,"trend_momentum":0~1,"liquidity":0~1,"risk":0~1}
    signals: List[str]                   # 예: ["Price ≥ MA200","MA50 slope ↑","63D return +x%"]
    completeness: float                  # 입력 충족도(0~1)
    conf: float                          # 데이터 품질 기반 신뢰도(0~1)

class Evidence(TypedDict, total=False):
    id: str                              # 근거 ID (E-001 등)
    text: str                            # 한 줄 주장(팩트)
    source: str                          # URL
    date: Optional[str]                  # YYYY-MM-DD 또는 YYYY
    quote: Optional[str]                 # 출처 내 짧은 인용
    conf: float                          # 근거 품질(0~1)

class FilingItem(TypedDict, total=False):
    claims: List[Evidence]               # 사업 전개 관련 근거 문장 리스트(3~6 권장)
    coverage: float                      # 키워드 커버리지(제품/공장/지역/제휴/소프트웨어)
    conf: float                          # 평균 품질(conf)
    recency: Dict[str, Any]              # {"year_counts":{2025:n,...},"share_2024plus":0~1}
    insufficient_reasons: List[str]      # 부족 사유(있을 때만)

class CompanyCard(TypedDict, total=False):
    ticker: str
    quant_score: Optional[int]           # QuantScore
    signals: List[str]                   # 핵심 시그널 2~3개
    evidence_count: int                  # 근거 개수
```

### 3) Agent ↔ State (읽기/쓰기 매핑)
| Agent/Node | 읽기(READ) | 쓰기(WRITE) |
|---|---|---|
| **quant_analysis_agent** | `input.companies`, `shared.prices`, *(선택)*`shared.finviz` | `quant[ticker]=QuantItem`, `logs+=[]` |
| **filing_reader_agent** *(웹서치)* | `input.companies`, *(선택)*`shared.filings_index` | `filings[ticker]=FilingItem`, `eval_flags[ticker]["business"]`, `logs+=[]` |
| **merge_node** | `input.companies`, `quant`, `filings` | `merged.company_cards=[CompanyCard,...]` |
| **report_writer_agent** | `input.companies`, `quant`, `filings`, `merged`, *(선택)*`shared.report_path`, `shared.llm` | `report={"md_path":..., "artifacts":[]}`, `logs+=[]` |

> 규칙: `input.*`, `shared.*`는 **읽기 전용**. 각 에이전트는 **자기 영역만** 업데이트.

### 4) 최소 예시(State JSON)
```json
{
  "input": {"companies":[{"ticker":"TSLA"}, {"ticker":"NIO"}, {"ticker":"RIVN"}]},
  "shared": {"prices": {"TSLA": "OHLCV_df", "NIO": "OHLCV_df", "RIVN": "OHLCV_df"}, "report_path":"out/ev_report.md"},
  "eval_flags": {},
  "logs": []
}
```
> OHLCV DataFrame 컬럼은 **Open, High, Low, Close, Volume** 이어야 합니다(인덱스 reset).

---

## Directory Structure
```
├── agents/
│   ├── quant_scorer_module.py        # QuantScore 계산 에이전트
│   ├── filing_websearch_module.py    # 웹서치 근거 수집 에이전트(부족 시 1회 보강)
│   └── report_writer_module.py       # 리포트 생성 에이전트
├── loaders/
│   └── price_loader_fdr.py           # FinanceDataReader OHLCV 로더
├── orchestration/
│   ├── graph_pipeline_supervisor.py  # LangGraph(명시적 supervisor + gate)
│   ├── graph_pipeline.py             # LangGraph(간단 병렬)
│   ├── run_supervisor_fdr.py         # FDR 기반 순차 러너
│   └── run_supervisor.py             # (대체) yfinance/CSV/더미 순차 러너
├── data/                             # (옵션) 로컬 문서/CSV
├── outputs/                          # 결과/리포트 저장 (out/)
└── README.md
```

## How to Run (Quickstart)
```bash
# 설치
pip install finance-datareader tavily langchain-core langchain-community beautifulsoup4 pandas numpy

# (웹서치) Tavily 키
export TAVILY_API_KEY="YOUR_KEY"

# 실행 (명시적 Supervisor 버전)
python orchestration/graph_pipeline_supervisor.py

# 또는 간단 병렬
python orchestration/graph_pipeline.py

# 또는 FDR 순차 러너
python orchestration/run_supervisor_fdr.py
```

## Contributors 
- **고경남** : Agent Design, Quant Scoring, Orchestration  
