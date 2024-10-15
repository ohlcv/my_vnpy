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
from DataAPI.csvAPI import CSV_API
from Plot.PlotDriver import CPlotDriver  # 导入绘图驱动类，用于绘制缠论分析结果
import os
from Config import config


if __name__ == "__main__":
    # 加载配置文件
    config_file = os.path.join(".", "Config", "config.json")
    config_data = config.load_config(config_file)

    # 解析配置文件内容
    chan_config = CChanConfig(config_data["chan_config"])
    plot_config = config_data["plot_config"]
    plot_para = config_data["plot_para"]
    chan_config.trigger_step = True  # 启用逐步加载

    code = "BTCUSDT"  # 设置交易品种，如BTCUSDT（比特币/美元）
    begin_time = "2024-09-30"
    end_time = "2024-10-07"
    data_src_type = DATA_SRC.CSV  # 使用CSV数据源
    k_type = KL_TYPE.K_5M
    lv_list = [k_type]  # 级别列表

    # 初始化数据源（CSV）
    data_src = CSV_API(
        code,
        k_type=k_type,
        begin_time=begin_time,
        end_time=end_time,
        autype=AUTYPE.QFQ,  # 前复权
        # file_path="./Data",  # 新增参数：保存CSV的目录路径
    )  # 初始化数据源实例

    # 初始化CChan实例，并传入相关配置参数
    chan = CChan(
        code=code,
        data_src=data_src_type,
        lv_list=lv_list,
        begin_time=begin_time,
        end_time=end_time,
        config=chan_config,
        autype=AUTYPE.QFQ,  # 设置前复权，虽然没实际使用
    )

    # 定义保存图片和数据的根目录
    png_root = os.path.join("..", "Png", code, k_type.name, f"{begin_time}-{end_time}")
    os.makedirs(png_root, exist_ok=True)

    # 初始化变量
    # data = data_src.get_kl_data()
    # for coint, klu in enumerate(data, start=1):
    #     print(f"当前计数：{coint}，当前k线：{klu}")

    # 依次获取每一根K线进行分析
    previous_fig = None  # 用于保存上一个图形对象
    for coint, chan_snapshot in enumerate(chan.step_load(), start=1):  # 从1开始计数
        cur_lv_chan = chan_snapshot[0]
        last_klc = cur_lv_chan[-1]
        last_klu = last_klc[-1]
        last_time = last_klu.time
        print(f"当前k线：{last_klu}")
        # bsp_list = chan_snapshot.get_bsp()  # 获取买卖点列表
        # last_bsp = bsp_list[-1] if bsp_list else None
        # 使用三元表达式打印 last_bsp 的属性
        # print(f"bi: {last_bsp.bi if hasattr(last_bsp, 'bi') else 'Not available'}")
        # print(
        #     f"features: {vars(last_bsp.features) if hasattr(last_bsp, 'features') else 'Not available'}"
        # )
        # print(
        #     f"is_buy: {last_bsp.is_buy if hasattr(last_bsp, 'is_buy') else 'Not available'}"
        # )
        # print(
        #     f"is_segbsp: {last_bsp.is_segbsp if hasattr(last_bsp, 'is_segbsp') else 'Not available'}"
        # )
        # print(f"klu: {last_bsp.klu if hasattr(last_bsp, 'klu') else 'Not available'}")
        # print(
        #     f"type: {last_bsp.type if hasattr(last_bsp, 'type') else 'Not available'}"
        # )
        # print(
        #     f"relate_bsp1: {last_bsp.relate_bsp1 if hasattr(last_bsp, 'relate_bsp1') else 'Not available'}"
        # )

        # 创建绘图驱动类实例，并绘制图形
        plot_driver = CPlotDriver(
            chan,
            plot_config=plot_config,
            plot_para=plot_para,
        )
        plot_driver.figure.show()  # 显示绘图结果

        # plt.show(block=False)   # 显示图形并非阻塞
        # plt.pause(0.1)  # 暂停0.1秒钟以便显示

        # 如果有上一个图形对象，则关闭它
        if previous_fig:
            plt.close(previous_fig)

        # 保存绘图结果到图片
        img_path = os.path.join(png_root, f"{coint}.png")
        plot_driver.save2img(img_path)

        # 保存 CChan 实例到同一目录
        chan_pickle_path = os.path.join(png_root, f"chan.pkl")
        config.save_chan_instance(chan, chan_pickle_path)

        previous_fig = plot_driver.figure  # 更新上一张图形对象
        plt.close("all")

    plt.close("all")  # 最后关闭所有未关闭的图形窗口
