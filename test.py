from data.data_maker import category_devider
from data.finviz_crawler import get_fundamental

if __name__ == "__main__":
    df = category_devider()
    df = get_fundamental(df)