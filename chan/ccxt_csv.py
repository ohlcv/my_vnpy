from matplotlib import pyplot as plt
from Common.CEnum import (
    DATA_SRC,
    KL_TYPE,
)  # 导入一些枚举类型，用于配置和标记买卖点类型、K线类型等

# from DataAPI.BaoStockAPI import CBaoStock
from DataAPI.ccxt import CCXT  # 导入CCXT数据接口类，用于获取加密货币的历史K线数据

if __name__ == "__main__":
    code = "BTCUSDT"  # 设置交易品种，如BTCUSDT（比特币/美元）
    begin_time = "2010-10-01"  # 设置开始时间
    end_time = None  # 设置结束时间（None表示到最新时间）
    data_src_type = DATA_SRC.CCXT  # 设置数据来源，CCXT表示通过CCXT库获取数据
    k_type = KL_TYPE.K_5M
    lv_list = [k_type]

    # 初始化数据源（CCXT）
    data_src = CCXT(
        code,
        k_type=k_type,
        begin_time=begin_time,
        end_time=end_time,
        save_csv=True,  # 新增参数：是否保存数据到CSV
        # csv_path="./Data",  # 新增参数：保存CSV的目录路径
    )  # 初始化数据源实例

    # 初始化变量
    data = data_src.get_kl_data()
    # 依次获取每一根K线进行分析
    for coint, klu in enumerate(data, start=1):  # 获取单根K线数据
        print(coint, klu)

    CCXT.do_close()  # 关闭CCXT数据源连接
