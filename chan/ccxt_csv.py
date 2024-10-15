from matplotlib import pyplot as plt
from Chan import CChan  # 导入缠论核心计算类
from ChanConfig import CChanConfig  # 导入缠论配置类
from Common.CEnum import (
    AUTYPE,
    BSP_TYPE,
    DATA_SRC,
    FX_TYPE,
    KL_TYPE,
)  # 导入一些枚举类型，用于配置和标记买卖点类型、K线类型等

# from DataAPI.BaoStockAPI import CBaoStock
from DataAPI.ccxt import CCXT  # 导入CCXT数据接口类，用于获取加密货币的历史K线数据
from Plot.PlotDriver import CPlotDriver  # 导入绘图驱动类，用于绘制缠论分析结果
import os

if __name__ == "__main__":
    code = "BTCUSDT"  # 设置交易品种，如BTCUSDT（比特币/美元）
    begin_time = "2024-10-01"  # 设置开始时间
    end_time = None  # 设置结束时间（None表示到最新时间）
    data_src_type = DATA_SRC.CCXT  # 设置数据来源，CCXT表示通过CCXT库获取数据
    k_type = KL_TYPE.K_1M
    lv_list = [k_type]

    # 初始化数据源（CCXT）
    data_src = CCXT(
        code,
        k_type=k_type,
        begin_time=begin_time,
        end_time=end_time,
        autype=AUTYPE.QFQ,  # 前复权
        save_csv=True,  # 新增参数：是否保存数据到CSV
        # csv_path="./Data",  # 新增参数：保存CSV的目录路径
    )  # 初始化数据源实例

    # 定义保存图片的根目录
    png_root = f"./Png/{code}/{k_type.name}"
    os.makedirs(png_root, exist_ok=True)  # 如果目录已存在，不会抛出异常

    # 初始化变量
    data = data_src.get_kl_data()
    # 依次获取每一根K线进行分析
    for coint, klu in enumerate(data, start=1):  # 获取单根K线数据
        print(coint, klu)

    CCXT.do_close()  # 关闭CCXT数据源连接
