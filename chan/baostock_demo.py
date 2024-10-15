from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, BSP_TYPE, DATA_SRC, FX_TYPE, KL_TYPE
from DataAPI.BaoStockAPI import CBaoStock
from Plot.PlotDriver import CPlotDriver
from matplotlib import pyplot as plt
import os

if __name__ == "__main__":
    """
    一个非常简单的策略，演示如何基于缠论买卖点来进行策略实现。
    策略逻辑：底分型（第一类买点）形成后开仓，顶分型（第一类卖点）形成后平仓。
    该代码主要用于展示如何从外部向CChan类输入K线数据并触发内部缠论计算。
    """
    code = "sh.000001"
    begin_time = "2000-01-01"
    end_time = None
    data_src_type = DATA_SRC.BAO_STOCK
    lv_list = [KL_TYPE.K_DAY]

    # 创建目标保存路径
    save_dir = f"./Png/{code}"
    os.makedirs(save_dir, exist_ok=True)  # 确保目标目录存在

    # 配置缠论参数
    config = CChanConfig(
        {
            "zs_combine": False,  # 是否进行中枢合并
            "bi_strict": False,  # 是否严格标记笔，如果是True，则标记笔的标准更严格
            "trigger_step": True,  # 是否启用跳跃触发策略
            "skip_step": 0,  # 跳过前面几根K线
            "divergence_rate": float("inf"),  # 设置1类买卖点背驰比例，默认为正无穷大
            "bsp2_follow_1": False,  # 2类买卖点是否必须跟在1类买卖点后面
            "bsp3_follow_1": False,  # 3类买卖点是否必须跟在1类买卖点后面
            "min_zs_cnt": 0,  # 1类买卖点至少要经历几个中枢
            "bs1_peak": True,  # 第一类买卖点是否使用峰值算法
            "macd_algo": "peak",  # MACD算法类型，默认为"area"
            "bs_type": "1,2,3a,1p,2s,3b",  # 买卖点类型
            "print_warning": True,  # 是否打印警告信息
            "zs_algo": "normal",  # 中枢算法类型，默认为"normal"
            "mean_metrics": [5, 20, 80],
            "cal_demark": False,
            "cal_rsi": False,
        }
    )

    # 初始化CChan实例，并传入相关配置参数
    chan = CChan(
        code=code,
        begin_time=begin_time,
        end_time=end_time,
        data_src=data_src_type,
        lv_list=lv_list,
        config=config,
        autype=AUTYPE.QFQ,  # 设置前复权，虽然没实际使用
    )

    # 初始化数据源
    CBaoStock.do_init()
    data_src = CBaoStock(
        code,
        k_type=KL_TYPE.K_DAY,  # 设置K线类型为日线
        begin_date=begin_time,
        end_date=end_time,
        autype=AUTYPE.QFQ,  # 前复权
    )  # 初始化数据源实例

    # 设置绘图配置参数
    plot_config = {
        "plot_kline": True,  # 是否绘制K线图
        "plot_kline_combine": True,  # 是否绘制合并K线
        "plot_bi": True,  # 是否绘制笔
        "plot_seg": True,  # 是否绘制线段
        "plot_segseg": False,  # 绘制线段的分段情况
        "plot_eigen": False,  # 是否绘制特征值
        "plot_zs": True,  # 是否绘制中枢
        "plot_macd": True,  # 是否绘制MACD指标
        "plot_mean": True,  # 是否绘制均值线（如均线）
        "plot_channel": False,  # 是否绘制通道
        "plot_bsp": True,  # 是否绘制买卖点
        "plot_segbsp": True,  # 是否绘制线段理论买卖点
        "plot_extrainfo": False,  # 是否绘制额外信息
        "plot_demark": True,  # 是否绘制DeMark指标
        "plot_marker": False,  # 是否绘制自定义文本标记
        "plot_rsi": False,  # 是否绘制RSI指标
        "plot_kdj": False,  # 是否绘制KDJ指标
        "plot_boll": True,
        "plot_tradeinfo": True,
    }

    # 设置绘图的参数选项
    plot_para = {
        "seg": {
            # "plot_trendline": True,  # 是否绘制趋势线
        },
        "bi": {
            "show_num": True,  # 显示笔的编号
            "disp_end": True,  # 显示笔的结束点
        },
        "figure": {
            "grid": None,
            "x_range": 200,  # 显示范围的X轴跨度
        },
        "marker": {
            # 自定义文本标记示例，可以标记某个时间点的某些事件
            # "markers": {  # text, position, color
            #     '2023/06/01': ('marker here', 'up', 'red'),
            #     '2023/06/08': ('marker here', 'down')
            # },
        },
        "tradeinfo": {"plot_curve": True, "info": "volume"},
    }

    # 初始化变量
    is_hold = False  # 是否持有仓位的标志
    last_buy_price = None  # 记录最后买入价格
    coint = 0  # 记录K线的计数器

    # 依次获取每一根K线进行分析
    for klu in data_src.get_kl_data():  # 获取单根K线数据
        coint += 1
        print(coint, klu)
        # 将新增的K线喂给CChan类以触发缠论计算
        chan.trigger_load({KL_TYPE.K_DAY: [klu]})
        # 每经过5根K线进行一次绘图并保存
        if coint > 0:
            plot_driver = CPlotDriver(
                chan,
                plot_config=plot_config,
                plot_para=plot_para,
            )
            # plot_driver.figure.show()  # 显示绘图结果
            # plt.show()
            plot_driver.save2img(f"./Png/{code}/{coint}.png")  # 保存绘图结果
            plt.close()

    CBaoStock.do_close()
