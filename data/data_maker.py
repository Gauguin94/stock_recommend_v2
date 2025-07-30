import os
import pandas as pd
from tqdm import tqdm
import yfinance as yf
from utils.const import TICKER_LIST
from utils.config_loader import load_config

def category_devider():
    ind_list = []
    sec_list = []

    print('섹터별-산업별 클래스 생성...')
    for ticker in tqdm(TICKER_LIST):
        ticker_object = yf.Ticker(ticker)
        info = ticker_object.info

        ind = info.get("industry")
        sec = info.get("sector")
        
        ind_list.append(ind)
        sec_list.append(sec)

    df = pd.DataFrame(columns=['ticker', 'sector', 'industry'])
    df['ticker'] = TICKER_LIST
    df['sector'] = sec_list
    df['industry'] = ind_list

    return df