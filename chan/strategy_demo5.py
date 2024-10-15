import json
import os
from typing import Dict, TypedDict

import xgboost as xgb  # 引入xgboost库，用于模型训练

from Chan import CChan
from ChanConfig import CChanConfig
from ChanModel.Features import CFeatures  # 导入CFeatures类，用于处理特征
from Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE
from Common.CTime import CTime
from Plot.PlotDriver import CPlotDriver
from Config import config


# 定义字典类型 T_SAMPLE_INFO，用于存储策略产出的买卖点的特征信息
class T_SAMPLE_INFO(TypedDict):
    feature: CFeatures  # 存储特征
    is_buy: bool  # 是否买入
    open_time: CTime  # 开仓时间


# 定义绘图函数，接收chan对象、买卖点标记以及图片路径
def plot(chan, plot_marker, img_path):
    # 配置绘图选项
    plot_config = {
        "plot_kline": True,  # 绘制K线
        "plot_bi": True,  # 绘制笔
        "plot_seg": True,  # 绘制线段
        "plot_zs": True,  # 绘制中枢
        "plot_bsp": True,  # 绘制买卖点
        "plot_marker": True,  # 绘制标记
    }
    # 配置绘图参数
    plot_para = {
        "figure": {
            "x_range": 400,  # 设置横轴范围
        },
        "marker": {"markers": plot_marker},  # 标记买卖点
    }
    # 创建绘图驱动实例
    plot_driver = CPlotDriver(
        chan,
        plot_config=plot_config,
        plot_para=plot_para,
    )
    # 将绘图保存为图片
    plot_driver.save2img(img_path)


# 定义获取策略特征的函数
def stragety_feature(last_klu):
    return {
        "open_klu_rate": (last_klu.close - last_klu.open)
        / last_klu.open,  # 计算开盘价和收盘价的比率
    }


if __name__ == "__main__":
    """
    本demo主要演示如何记录策略产出的买卖点的特征
    然后将这些特征作为样本，训练一个模型(以XGB为demo)
    用于预测买卖点的准确性

    请注意，demo训练预测都用的是同一份数据，这是不合理的，仅仅是为了演示
    """
    code = "BTCUSDT"  # 设置交易品种，如BTCUSDT（比特币/美元）
    begin_time = "2024-10-07"
    # end_time = "2024-10-07"
    end_time = None
    data_src = DATA_SRC.CSV  # 使用CSV数据源
    k_type = KL_TYPE.K_1M
    lv_list = [k_type]  # 级别列表

    png_root = os.path.join(
        "..",
        "machinelearning",
        "Png",
        code,
        lv_list[0].name,
        f"{begin_time}-{end_time}",
        "dome5",
    )
    os.makedirs(png_root, exist_ok=True)
    img_path = os.path.join(png_root, "label.png")
    # 设置保存模型的路径
    json_root = os.path.join(
        "..",
        "machinelearning",
        "json",
    )
    os.makedirs(json_root, exist_ok=True)
    json_path = os.path.join(json_root, "model.json")
    # 设置保存特征的路径
    feature_root = os.path.join(
        "..",
        "machinelearning",
        "feature",
    )
    os.makedirs(feature_root, exist_ok=True)

    config = CChanConfig(
        {
            "trigger_step": True,  # 打开开关！
            "bi_strict": True,
            "skip_step": 0,
            "divergence_rate": float("inf"),
            "bsp2_follow_1": False,
            "bsp3_follow_1": False,
            "min_zs_cnt": 0,
            "bs1_peak": False,
            "macd_algo": "peak",
            "bs_type": "1,2,3a,1p,2s,3b",
            "print_warning": True,
            "zs_algo": "normal",
        }
    )

    chan = CChan(
        code=code,
        begin_time=begin_time,
        end_time=end_time,
        data_src=data_src,
        lv_list=lv_list,
        config=config,
        autype=AUTYPE.QFQ,
    )

    bsp_dict: Dict[int, T_SAMPLE_INFO] = {}  # 存储策略产出的bsp的特征

    # 跑策略，保存买卖点的特征
    for chan_snapshot in chan.step_load():
        last_klu = chan_snapshot[0][-1][-1]  # 获取最后一个K线单元
        bsp_list = chan_snapshot.get_bsp()  # 获取买卖点
        if not bsp_list:
            continue  # 如果没有买卖点，跳过
        last_bsp = bsp_list[-1]  # 获取最新的买卖点

        cur_lv_chan = chan_snapshot[0]  # 当前级别缠论对象
        if (
            last_bsp.klu.idx not in bsp_dict
            and cur_lv_chan[-2].idx == last_bsp.klu.klc.idx
        ):
            # 假如策略是：买卖点分形第三元素出现时交易
            bsp_dict[last_bsp.klu.idx] = {
                "feature": last_bsp.features,
                "is_buy": last_bsp.is_buy,
                "open_time": last_klu.time,
            }
            bsp_dict[last_bsp.klu.idx]["feature"].add_feat(
                stragety_feature(last_klu)
            )  # 开仓K线特征
            print(last_bsp.klu.time, last_bsp.is_buy)

    # 生成libsvm样本特征
    bsp_academy = [bsp.klu.idx for bsp in chan.get_bsp()]  # 获取所有买卖点
    feature_meta = {}  # 特征元数据字典
    cur_feature_idx = 0  # 当前特征索引
    plot_marker = {}  # 绘图标记
    fid = open(f"{feature_root}\\feature.libsvm", "w")  # 打开libsvm文件写入样本特征
    for bsp_klu_idx, feature_info in bsp_dict.items():
        label = int(bsp_klu_idx in bsp_academy)  # 设置买卖点标签
        features = []  # 特征列表
        for feature_name, value in feature_info["feature"].items():
            if feature_name not in feature_meta:
                feature_meta[feature_name] = cur_feature_idx
                cur_feature_idx += 1
            features.append((feature_meta[feature_name], value))
        features.sort(key=lambda x: x[0])  # 按特征索引排序
        feature_str = " ".join([f"{idx}:{value}" for idx, value in features])
        fid.write(f"{label} {feature_str}\n")  # 写入libsvm格式数据
        plot_marker[feature_info["open_time"].to_str()] = (
            "√" if label else "×",
            "down" if feature_info["is_buy"] else "up",
        )
    fid.close()

    # 保存特征元数据
    with open(f"{feature_root}\\feature.meta", "w") as fid:
        # meta保存下来，实盘预测时特征对齐用
        fid.write(json.dumps(feature_meta))

    # 画图检查label是否正确
    plot(chan, plot_marker, img_path)

    # 加载样本文件并训练模型
    dtrain = xgb.DMatrix(
        f"{feature_root}\\feature.libsvm?format=libsvm"
    )  # 加载libsvm样本
    param = {
        "max_depth": 2,  # 最大深度
        "eta": 0.3,  # 学习率
        "objective": "binary:logistic",  # 目标函数
        "eval_metric": "auc",  # 评估指标
    }
    # 初始化一个字典，用于存储评估结果
    evals_result = {}

    # 使用XGBoost训练一个模型
    bst = xgb.train(
        param,  # 训练参数
        dtrain=dtrain,  # 训练数据集
        num_boost_round=10,  # 提升迭代的次数
        evals=[(dtrain, "train")],  # 评估数据集，这里使用了训练集作为评估集
        evals_result=evals_result,  # 将评估结果存储到这个字典中
        verbose_eval=True,  # 打印出评估信息
    )

    # 将训练好的模型保存为JSON格式
    bst.save_model(json_path)

    # 加载模型
    model = xgb.Booster()  # 创建一个空的Booster对象
    model.load_model(json_path)  # 从JSON文件中加载模型

    # 使用加载的模型进行预测
    print(model.predict(dtrain))  # 打印出对训练集的预测结果
