from enum import Enum, auto
from typing import Literal


class DATA_SRC(Enum):
    """
    数据来源枚举，定义不同的数据获取渠道。
    """

    BAO_STOCK = auto()  # 来自 BaoStock 的数据
    CCXT = auto()  # 来自 CCXT 库的数据（加密货币交易所接口）
    CSV = auto()  # 来自 CSV 文件的数据


class KL_TYPE(Enum):
    """
    K 线类型枚举，定义不同时间周期的 K 线。
    """

    K_1M = auto()  # 1 分钟 K 线
    K_DAY = auto()  # 日 K 线
    K_WEEK = auto()  # 周 K 线
    K_MON = auto()  # 月 K 线
    K_YEAR = auto()  # 年 K 线
    K_5M = auto()  # 5 分钟 K 线
    K_15M = auto()  # 15 分钟 K 线
    K_30M = auto()  # 30 分钟 K 线
    K_60M = auto()  # 60 分钟 K 线
    K_3M = auto()  # 3 分钟 K 线
    K_QUARTER = auto()  # 季度 K 线


class KLINE_DIR(Enum):
    """
    K 线方向枚举，定义 K 线的走势方向。
    """

    UP = auto()  # 向上
    DOWN = auto()  # 向下
    COMBINE = auto()  # 合并
    INCLUDED = auto()  # 包含


class FX_TYPE(Enum):
    """
    分型类型枚举，定义 K 线的分型状态。
    """

    BOTTOM = auto()  # 底部分型
    TOP = auto()  # 顶部分型
    UNKNOWN = auto()  # 未知分型


class BI_DIR(Enum):
    """
    笔方向枚举，定义笔（趋势线）的方向。
    """

    UP = auto()  # 向上笔
    DOWN = auto()  # 向下笔


class BI_TYPE(Enum):
    """
    笔类型枚举，定义不同类型的笔。
    """

    UNKNOWN = auto()  # 未知类型
    STRICT = auto()  # 严格笔
    SUB_VALUE = auto()  # 次高低点成笔
    TIAOKONG_THRED = auto()  # 调控阈值笔
    DAHENG = auto()  # 大横笔
    TUIBI = auto()  # 推笔
    UNSTRICT = auto()  # 非严格笔
    TIAOKONG_VALUE = auto()  # 调控值笔


# 定义 BSP 的主类型字面量类型，仅允许 '1', '2', '3' 三种值
BSP_MAIN_TYPE = Literal["1", "2", "3"]


class BSP_TYPE(Enum):
    """
    买卖点类型枚举，定义不同类型的买卖点。
    """

    T1 = "1"  # 类型1
    T1P = "1p"  # 类型1的子类型p
    T2 = "2"  # 类型2
    T2S = "2s"  # 类型2的子类型s
    T3A = "3a"  # 类型3a，中枢在1类后面
    T3B = "3b"  # 类型3b，中枢在1类前面

    def main_type(self) -> BSP_MAIN_TYPE:
        """
        获取 BSP 类型的主类型部分（'1', '2', 或 '3'）。

        返回:
            BSP_MAIN_TYPE: 主类型字面量。
        """
        return self.value[0]  # type: ignore


class AUTYPE(Enum):
    """
    调整类型枚举，定义不同的价格调整方式。
    """

    QFQ = auto()  # 前复权
    HFQ = auto()  # 后复权
    NONE = auto()  # 无复权


class TREND_TYPE(Enum):
    """
    趋势类型枚举，定义不同的趋势分析方法。
    """

    MEAN = "mean"  # 均值趋势
    MAX = "max"  # 最大值趋势
    MIN = "min"  # 最小值趋势


class TREND_LINE_SIDE(Enum):
    """
    趋势线位置枚举，定义趋势线在价格图表中的位置。
    """

    INSIDE = auto()  # 趋势线在内部
    OUTSIDE = auto()  # 趋势线在外部


class LEFT_SEG_METHOD(Enum):
    """
    左侧线段方法枚举，定义左侧线段的处理方式。
    """

    ALL = auto()  # 全部线段
    PEAK = auto()  # 峰值线段


class FX_CHECK_METHOD(Enum):
    """
    分型检查方法枚举，定义分型的验证方式。
    """

    STRICT = auto()  # 严格检查
    LOSS = auto()  # 损失检查
    HALF = auto()  # 半检查
    TOTALLY = auto()  # 完全检查


class SEG_TYPE(Enum):
    """
    线段类型枚举，定义不同类型的线段。
    """

    BI = auto()  # 笔线段
    SEG = auto()  # 其他线段


class MACD_ALGO(Enum):
    """
    MACD 算法枚举，定义不同的 MACD 计算方法。
    """

    AREA = auto()  # 区域计算
    PEAK = auto()  # 峰值计算
    FULL_AREA = auto()  # 全区域计算
    DIFF = auto()  # 差值计算
    SLOPE = auto()  # 斜率计算
    AMP = auto()  # 振幅计算
    VOLUMN = auto()  # 成交量计算
    AMOUNT = auto()  # 成交额计算
    VOLUMN_AVG = auto()  # 成交量均值计算
    AMOUNT_AVG = auto()  # 成交额均值计算
    TURNRATE_AVG = auto()  # 换手率均值计算
    RSI = auto()  # 相对强弱指数计算


class DATA_FIELD:
    """
    数据字段常量类，定义常用的数据字段名称。
    """

    FIELD_TIMESTAMP = "timestamp"  # 时间戳
    FIELD_TIME = "time_key"  # 时间键
    FIELD_OPEN = "open"  # 开盘价
    FIELD_HIGH = "high"  # 最高价
    FIELD_LOW = "low"  # 最低价
    FIELD_CLOSE = "close"  # 收盘价
    FIELD_VOLUME = "volume"  # 成交量
    FIELD_TURNOVER = "turnover"  # 成交额
    FIELD_TURNRATE = "turnover_rate"  # 换手率


# 定义交易信息列表，包含需要关注的字段
TRADE_INFO_LST = [
    DATA_FIELD.FIELD_VOLUME,  # 成交量
    DATA_FIELD.FIELD_TURNOVER,  # 成交额
    DATA_FIELD.FIELD_TURNRATE,  # 换手率
]
