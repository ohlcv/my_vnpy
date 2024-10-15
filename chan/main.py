import json
from matplotlib import pyplot as plt
from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE
from Plot.AnimatePlotDriver import CAnimateDriver
from Plot.PlotDriver import CPlotDriver
from DataAPI.csvAPI import CSV_API


def load_config(file_path):
    with open(file_path, "r") as f:
        config_data = json.load(f)
    return config_data


if __name__ == "__main__":
    # 加载配置文件
    config_file = "./Config/config.json"
    config_data = load_config(config_file)

    # 解析配置文件内容
    chan_config = CChanConfig(config_data["chan_config"])
    plot_config = config_data["plot_config"]
    plot_para = config_data["plot_para"]

    # 基础设置
    code = "BTCUSDT"
    begin_time = "2024-10-08"
    end_time = None
    data_src_type = DATA_SRC.CSV
    lv_list = [KL_TYPE.K_1M]

    # 实例化缠论对象
    chan = CChan(
        code=code,
        begin_time=begin_time,
        end_time=end_time,
        data_src=data_src_type,
        lv_list=lv_list,
        config=chan_config,
        autype=AUTYPE.QFQ,
    )

    # 绘图或动画
    if not chan_config.trigger_step:
        plot_driver = CPlotDriver(
            chan,
            plot_config=plot_config,
            plot_para=plot_para,
        )
        plot_driver.figure.show()
        plt.show()
    else:
        CAnimateDriver(
            chan,
            plot_config=plot_config,
            plot_para=plot_para,
        )
