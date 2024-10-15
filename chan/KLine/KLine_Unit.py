import copy
from typing import Dict, Optional

# 从 Common 模块导入枚举类型和异常类
from ..Common.CEnum import DATA_FIELD, TRADE_INFO_LST, TREND_TYPE
from ..Common.ChanException import CChanException, ErrCode
from ..Common.CTime import CTime

# 从 Math 模块导入各种技术指标类
from ..Math.BOLL import BOLL_Metric, BollModel
from ..Math.Demark import CDemarkEngine, CDemarkIndex
from ..Math.KDJ import KDJ
from ..Math.MACD import CMACD, CMACD_item
from ..Math.RSI import RSI
from ..Math.TrendModel import CTrendModel

# 从同级目录导入交易信息类
from .TradeInfo import CTradeInfo


class CKLine_Unit:
    """
    CKLine_Unit 类用于表示单个 K 线单元，包含价格信息、技术指标和关联的其他 K 线单元。
    """

    def __init__(self, kl_dict, autofix=False):
        """
        初始化 CKLine_Unit 对象。

        参数：
            kl_dict (dict): 包含 K 线数据的字典。
            autofix (bool): 是否自动修复数据中的异常值（默认为 False）。
        """
        # 初始化类型为 None
        self.kl_type = None

        # 获取时间戳，如果存在的话
        self.timestamp = (
            kl_dict[DATA_FIELD.FIELD_TIMESTAMP]
            if DATA_FIELD.FIELD_TIMESTAMP in kl_dict
            else None
        )

        # 设置时间对象
        self.time: CTime = kl_dict[DATA_FIELD.FIELD_TIME]

        # 设置开盘、收盘、最高、最低价
        self.close = kl_dict[DATA_FIELD.FIELD_CLOSE]
        self.open = kl_dict[DATA_FIELD.FIELD_OPEN]
        self.high = kl_dict[DATA_FIELD.FIELD_HIGH]
        self.low = kl_dict[DATA_FIELD.FIELD_LOW]

        # 检查并可能修复数据
        self.check(autofix)

        # 初始化交易信息
        self.trade_info = CTradeInfo(kl_dict)

        # 初始化 DeMark 指标
        self.demark: CDemarkIndex = CDemarkIndex()

        # 初始化子级 K 线列表和父级 K 线引用
        self.sub_kl_list = []  # 次级别 KLU 列表
        self.sup_kl: Optional[CKLine_Unit] = None  # 指向更高级别 KLU

        # 延迟导入 CKLine 类，避免循环导入
        from ..KLine.KLine import CKLine

        # 初始化指向 KLine 对象的引用
        self.__klc: Optional[CKLine] = None  # 指向 KLine

        # 初始化趋势字典，存储不同类型的趋势指标
        self.trend: Dict[TREND_TYPE, Dict[int, float]] = {}  # int -> float

        # 设置涨停和跌停标志，0 表示普通，-1 表示跌停，1 表示涨停
        self.limit_flag = 0  # 0:普通 -1:跌停，1:涨停

        # 初始化前一个和后一个 K 线单元的引用
        self.pre: Optional[CKLine_Unit] = None
        self.next: Optional[CKLine_Unit] = None

        # 设置索引为 -1，后续可能会被更新
        self.set_idx(-1)

    def __deepcopy__(self, memo):
        """
        实现深拷贝方法，确保所有嵌套对象也被正确拷贝。

        参数：
            memo (dict): 缓存字典，避免重复拷贝。

        返回：
            CKLine_Unit: 深拷贝后的 CKLine_Unit 对象。
        """
        # 创建一个新的字典，只包含基础价格和时间字段
        _dict = {
            DATA_FIELD.FIELD_TIME: self.time,
            DATA_FIELD.FIELD_CLOSE: self.close,
            DATA_FIELD.FIELD_OPEN: self.open,
            DATA_FIELD.FIELD_HIGH: self.high,
            DATA_FIELD.FIELD_LOW: self.low,
        }

        # 将交易信息中的指标添加到字典中
        for metric in TRADE_INFO_LST:
            if metric in self.trade_info.metric:
                _dict[metric] = self.trade_info.metric[metric]

        # 创建一个新的 CKLine_Unit 对象
        obj = CKLine_Unit(_dict)

        # 深拷贝 DeMark 指标和趋势指标
        obj.demark = copy.deepcopy(self.demark, memo)
        obj.trend = copy.deepcopy(self.trend, memo)

        # 复制涨停标志
        obj.limit_flag = self.limit_flag

        # 深拷贝技术指标（如果存在）
        obj.macd = copy.deepcopy(self.macd, memo)
        obj.boll = copy.deepcopy(self.boll, memo)
        if hasattr(self, "rsi"):
            obj.rsi = copy.deepcopy(self.rsi, memo)
        if hasattr(self, "kdj"):
            obj.kdj = copy.deepcopy(self.kdj, memo)

        # 复制索引
        obj.set_idx(self.idx)

        # 将当前对象的 ID 添加到 memo 中，避免重复拷贝
        memo[id(self)] = obj

        return obj

    @property
    def klc(self):
        """
        获取关联的 CKLine 对象。

        返回：
            CKLine: 关联的 CKLine 对象。
        """
        assert self.__klc is not None
        return self.__klc

    def set_klc(self, klc):
        """
        设置关联的 CKLine 对象。

        参数：
            klc (CKLine): 需要关联的 CKLine 对象。
        """
        self.__klc = klc

    @property
    def idx(self):
        """
        获取当前 K 线单元的索引。

        返回：
            int: 当前索引值。
        """
        return self.__idx

    def set_idx(self, idx):
        """
        设置当前 K 线单元的索引。

        参数：
            idx (int): 需要设置的索引值。
        """
        self.__idx: int = idx

    def __str__(self):
        """
        返回当前 K 线单元的字符串表示。

        返回：
            str: K 线单元的详细信息字符串。
        """
        return f"{self.idx}:{self.time}/{self.kl_type} open={self.open} close={self.close} high={self.high} low={self.low} {self.trade_info}"

    def check(self, autofix=False):
        """
        检查 K 线数据的有效性，确保最低价和最高价正确。

        参数：
            autofix (bool): 如果为 True，自动修复异常数据，否则抛出异常。
        """
        # 检查最低价是否为所有价格中的最小值
        if self.low > min([self.low, self.open, self.high, self.close]):
            if autofix:
                self.low = min(
                    [self.low, self.open, self.high, self.close]
                )  # 自动修复最低价
            else:
                # 抛出自定义异常，提示数据无效
                raise CChanException(
                    f"{self.time} low price={self.low} is not min of [low={self.low}, open={self.open}, high={self.high}, close={self.close}]",
                    ErrCode.KL_DATA_INVALID,
                )
        # 检查最高价是否为所有价格中的最大值
        if self.high < max([self.low, self.open, self.high, self.close]):
            if autofix:
                self.high = max(
                    [self.low, self.open, self.high, self.close]
                )  # 自动修复最高价
            else:
                # 抛出自定义异常，提示数据无效
                raise CChanException(
                    f"{self.time} high price={self.high} is not max of [low={self.low}, open={self.open}, high={self.high}, close={self.close}]",
                    ErrCode.KL_DATA_INVALID,
                )

    def add_children(self, child):
        """
        添加子级 K 线单元。

        参数：
            child (CKLine_Unit): 需要添加的子级 K 线单元。
        """
        self.sub_kl_list.append(child)

    def set_parent(self, parent: "CKLine_Unit"):
        """
        设置父级 K 线单元。

        参数：
            parent (CKLine_Unit): 父级 K 线单元。
        """
        self.sup_kl = parent

    def get_children(self):
        """
        生成器方法，返回所有子级 K 线单元。

        生成：
            CKLine_Unit: 子级 K 线单元。
        """
        yield from self.sub_kl_list

    def _low(self):
        """
        获取最低价。

        返回：
            float: 当前最低价。
        """
        return self.low

    def _high(self):
        """
        获取最高价。

        返回：
            float: 当前最高价。
        """
        return self.high

    def set_metric(self, metric_model_lst: list) -> None:
        """
        设置技术指标，根据传入的指标模型列表更新相应的指标值。

        参数：
            metric_model_lst (list): 技术指标模型列表。
        """
        for metric_model in metric_model_lst:
            if isinstance(metric_model, CMACD):
                # 计算并设置 MACD 指标
                self.macd: CMACD_item = metric_model.add(self.close)
            elif isinstance(metric_model, CTrendModel):
                # 计算并设置趋势指标
                if metric_model.type not in self.trend:
                    self.trend[metric_model.type] = {}
                self.trend[metric_model.type][metric_model.T] = metric_model.add(
                    self.close
                )
            elif isinstance(metric_model, BollModel):
                # 计算并设置布林带指标
                self.boll: BOLL_Metric = metric_model.add(self.close)
            elif isinstance(metric_model, CDemarkEngine):
                # 更新 DeMark 指标
                self.demark = metric_model.update(
                    idx=self.idx, close=self.close, high=self.high, low=self.low
                )
            elif isinstance(metric_model, RSI):
                # 计算并设置 RSI 指标
                self.rsi = metric_model.add(self.close)
            elif isinstance(metric_model, KDJ):
                # 计算并设置 KDJ 指标
                self.kdj = metric_model.add(self.high, self.low, self.close)

    def get_parent_klc(self):
        """
        获取父级 K 线单元的 CKLine 对象。

        返回：
            CKLine: 父级 K 线单元的 CKLine 对象。
        """
        assert self.sup_kl is not None
        return self.sup_kl.klc

    def include_sub_lv_time(self, sub_lv_t: str) -> bool:
        """
        检查当前 K 线单元及其子级是否包含指定时间。

        参数：
            sub_lv_t (str): 需要检查的时间字符串。

        返回：
            bool: 如果包含，返回 True，否则返回 False。
        """
        if self.time.to_str() == sub_lv_t:
            return True
        for sub_klu in self.sub_kl_list:
            if sub_klu.time.to_str() == sub_lv_t:
                return True
            if sub_klu.include_sub_lv_time(sub_lv_t):
                return True
        return False

    def set_pre_klu(self, pre_klu: Optional["CKLine_Unit"]):
        """
        设置前一个 K 线单元，并建立双向链接。

        参数：
            pre_klu (CKLine_Unit | None): 前一个 K 线单元。如果为 None，则不进行任何操作。
        """
        if pre_klu is None:
            return
        pre_klu.next = self  # 将当前 K 线单元设置为前一个 K 线单元的下一个
        self.pre = pre_klu  # 将前一个 K 线单元设置为当前的前一个
