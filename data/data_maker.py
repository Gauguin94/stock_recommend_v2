import pandas as pd
from tqdm import tqdm
from yahooquery import Ticker
from utils.const import TICKER_LIST
from utils.config_loader import load_config

def category_devider():
    ind_list = []
    sec_list = []

    print('섹터별-산업별 클래스 생성...')
    for ticker in tqdm(TICKER_LIST):
        try:
            t = Ticker(ticker)
            profile = t.asset_profile
            # 일부 티커는 정보가 없을 수도 있으니 안전하게 처리
            ind = profile.get(ticker, {}).get("industry", None)
            sec = profile.get(ticker, {}).get("sector", None)
        except Exception as e:
            print(f"[{ticker}] 에러 발생: {e}")
            ind, sec = None, None

        ind_list.append(ind)
        sec_list.append(sec)

    df = pd.DataFrame({
        'ticker': TICKER_LIST,
        'sector': sec_list,
        'industry': ind_list
    })

    return df

# import os
# import pandas as pd
# from tqdm import tqdm
# import yfinance as yf
# from utils.const import TICKER_LIST
# from utils.config_loader import load_config

# def category_devider():
#     ind_list = []
#     sec_list = []

#     print('섹터별-산업별 클래스 생성...')
#     for ticker in tqdm(TICKER_LIST):
#         ticker_object = yf.Ticker(ticker)
#         info = ticker_object.info

#         ind = info.get("industry")
#         sec = info.get("sector")
        
#         ind_list.append(ind)
#         sec_list.append(sec)

#     df = pd.DataFrame(columns=['ticker', 'sector', 'industry'])
#     df['ticker'] = TICKER_LIST
#     df['sector'] = sec_list
#     df['industry'] = ind_list

#     return df