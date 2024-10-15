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
from DataAPI.csvAPI import CSV_API
from Plot.PlotDriver import CPlotDriver  # 导入绘图驱动类，用于绘制缠论分析结果
import os
import json
import pickle


def load_config(file_path):
    with open(file_path, "r") as f:
        config_data = json.load(f)
    return config_data


if __name__ == "__main__":
    # 加载配置文件
    config_file = os.path.join(".", "Config", "config.json")
    config_data = load_config(config_file)

    # 解析配置文件内容
    chan_config = CChanConfig(config_data["chan_config"])
    plot_config = config_data["plot_config"]
    plot_para = config_data["plot_para"]
    chan_config.trigger_step = True

    code = "BTCUSDT"  # 设置交易品种，如BTCUSDT（比特币/美元）
    begin_time = "2024-10-01"  # 设置开始时间
    end_time = None  # 设置结束时间（None表示到最新时间）
    # data_src_type = DATA_SRC.CCXT  # 设置数据来源，CCXT表示通过CCXT库获取数据
    data_src_type = DATA_SRC.CSV
    k_type = KL_TYPE.K_1M
    lv_list = [k_type]

    # 初始化数据源（CCXT）
    # data_src = CCXT(
    #     code,
    #     k_type=k_type,
    #     begin_date=begin_time,
    #     end_date=end_time,
    #     autype=AUTYPE.QFQ,  # 前复权
    #     save_csv=True,  # 新增参数：是否保存数据到CSV
    #     # csv_path="./Data",  # 新增参数：保存CSV的目录路径
    # )  # 初始化数据源实例

    data_src = CSV_API(
        code,
        k_type=k_type,
        begin_date=begin_time,
        end_date=end_time,
        autype=AUTYPE.QFQ,  # 前复权
        # file_path="./Data",  # 新增参数：保存CSV的目录路径
    )  # 初始化数据源实例

    # 初始化CChan实例，并传入相关配置参数
    chan = CChan(
        code=code,
        data_src=data_src_type,
        lv_list=lv_list,
        config=chan_config,
        autype=AUTYPE.QFQ,  # 设置前复权，虽然没实际使用
    )

    # 定义保存图片的根目录
    png_root = os.path.join("..", "Png", code, k_type.name)
    os.makedirs(png_root, exist_ok=True)

    # 初始化变量
    data = data_src.get_kl_data()
    # 清除所有数据
    chan.do_init()

    # 依次获取每一根K线进行分析
    # for coint, klu in enumerate(data, start=1):  # 从1开始计数
    for coint, chan_snapshot in enumerate(chan.step_load(), start=1):  # 从1开始计数
        cur_lv_chan = chan_snapshot[0]
        last_klu = cur_lv_chan[-1][-1]
        last_time = last_klu.time
        print(f"当前k线：{last_klu}")
        # 将新增的K线喂给CChan类以触发缠论计算
        # chan.trigger_load({k_type: [klu]})
        if coint > 0:
            plot_driver = CPlotDriver(
                chan,
                plot_config=plot_config,
                plot_para=plot_para,
            )
            plot_driver.figure.show()  # 显示绘图结果
            plt.show(block=False)  # 非阻塞显示图形
            plt.pause(0.1)  # 暂停1秒
            plot_driver.save2img(os.path.join(png_root, f"{coint}.png"))  # 保存绘图结果
            plt.close()  # 关闭图形窗口

    # CCXT.do_close()  # 关闭CCXT数据源连接
