import requests
import os
import pandas as pd
from tqdm import tqdm
from bs4 import BeautifulSoup
import time

def str2float(data):
    fper = float(data.get("Forward P/E", "N/A"))
    per = float(data.get("P/E", "N/A"))
    pbr = float(data.get("P/B", "N/A"))
    roe = float(data.get("ROE", "N/A").strip('%'))
    roa = float(data.get("ROA", "N/A").strip('%'))
    eps = float(data.get("EPS (ttm)", "N/A"))
    return fper, per, pbr, roe, roa, eps

def get_fundamental(df):
    ticker_list = []
    sec_list = []
    ind_list = []
    fper_list = []
    per_list = []
    pbr_list = []
    roe_list = []
    roa_list = []
    eps_list = []
    country_list = []

    print('펀더멘탈 크롤링...')
    for elem in tqdm(df.itertuples()):
        url = f"https://finviz.com/quote.ashx?t={elem.ticker}&p=d"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
        }
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        # 스냅샷 테이블 찾기
        snapshot_table = soup.find("table", class_="snapshot-table2")

        # 데이터를 키-값으로 저장
        data = {}
        rows = snapshot_table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            for i in range(0, len(cells), 2):
                key = cells[i].get_text()
                value = cells[i+1].get_text()
                data[key] = value

        try:
            fper, per, pbr, roe, roa, eps = str2float(data)
            ticker_list.append(elem.ticker)
            sec_list.append(elem.sector)
            ind_list.append(elem.industry)
            fper_list.append(fper)
            per_list.append(per)
            pbr_list.append(pbr)
            roe_list.append(roe)
            roa_list.append(roa)
            eps_list.append(eps)

            # === 국가 추출 부분 ===
            country_tag = soup.select_one("div.quote-links a[href*='geo_']")
            if country_tag:
                country = country_tag.text.strip()
            else:
                country = "N/A"
            country_list.append(country)
            time.sleep(1)
        except:
            time.sleep(1)
            continue

    df = pd.DataFrame(
        columns = [
            'ticker', 'sector', 'industry',
            'Forward_PER', 'PER',
            'PBR', 'ROE', 'ROA', 'EPS',
            'country'
        ]
    )

    df['ticker'] = ticker_list
    df['sector'] = sec_list
    df['industry'] = ind_list
    df['Forward_PER'] = fper_list
    df['PER'] = per_list
    df['PBR'] = pbr_list
    df['ROE'] = roe_list
    df['ROA'] = roa_list
    df['EPS'] = eps_list
    df['country'] = country_list

    df.to_csv('{}/data/output/fundamental.csv'.format(os.getcwd()), encoding='utf-8-sig', index=False)

    return df