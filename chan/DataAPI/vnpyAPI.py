# DataAPI/VnpyDataApi.py

import copy
from typing import Iterable, Optional, List
from datetime import datetime

from ..Common.CEnum import DATA_FIELD, KL_TYPE, AUTYPE
from ..Common.ChanException import CChanException, ErrCode
from ..Common.CTime import CTime
from ..KLine.KLine_Unit import CKLine_Unit
from vnpy.trader.database import get_database
from vnpy.trader.constant import Interval, Exchange
from vnpy.trader.object import BarData
from .CommonStockAPI import CCommonStockApi


class C_VnpyDataApi(CCommonStockApi):
    """
    自定义数据源类，继承自 CCommonStockApi，用于从 vn.py 获取K线数据。
    """

    def __init__(self, code, k_type=KL_TYPE.K_DAY, begin_time=None, end_time=None, autype=AUTYPE.QFQ):
        super(C_VnpyDataApi, self).__init__(code, k_type, begin_time, end_time, autype)

    @classmethod
    def do_init(cls):
        """
        初始化方法，如果需要与vn.py的数据库或其他资源交互，可以在这里实现。
        """
        # 如果需要，可以在这里进行数据库连接或其他初始化操作
        pass

    @classmethod
    def do_close(cls):
        """
        关闭方法，用于清理资源，如关闭数据库连接等。
        """
        # 如果需要，可以在这里进行资源清理操作
        pass

    def get_kl_data(self) -> Iterable[CKLine_Unit]:
        """
        获取K线数据的生成器方法，从vn.py的数据库中查询历史K线数据并生成CKLine_Unit对象。
        """
        return []
        # # 将KL_TYPE转换为vn.py的Interval
        # interval = self.convert_kltype_to_interval(self.k_type)

        # # 查询历史K线数据
        # bars: List[BarData] = get_database().load_bar_data( # 修改使用方式
        #     symbol=self.code,
        #     exchange=Exchange.SZSE if self.code.startswith("sz.") else Exchange.SHSE,
        #     interval=interval,
        #     start=self.begin_time,
        #     end=self.end_time,
        #     gateway_name="CTP"  # 根据你的实际Gateway名称调整
        # )

        # if not bars:
        #     raise CChanException("未获取到任何K线数据", ErrCode.NO_DATA)

        # for bar in bars:
        #     # 将vn.py的BarData转换为CKLine_Unit所需的字典
        #     item_dict = {
        #         DATA_FIELD.FIELD_TIME: CTime.from_datetime(bar.datetime),
        #         DATA_FIELD.FIELD_OPEN: float(bar.open_price),
        #         DATA_FIELD.FIELD_CLOSE: float(bar.close_price),
        #         DATA_FIELD.FIELD_HIGH: float(bar.high_price),
        #         DATA_FIELD.FIELD_LOW: float(bar.low_price),
        #     }

        #     # 可选字段
        #     if bar.volume is not None:
        #         item_dict[DATA_FIELD.FIELD_VOLUME] = float(bar.volume)
        #     if bar.turnover is not None:
        #         item_dict[DATA_FIELD.FIELD_TURNOVER] = float(bar.turnover)
        #     if bar.open_interest is not None:
        #         item_dict[DATA_FIELD.FIELD_TURNRATE] = float(bar.open_interest)  # 假设open_interest对应TURNRATE

        #     # 创建并yield CKLine_Unit对象
        #     yield CKLine_Unit(item_dict)
            

    def convert_kltype_to_interval(self, k_type: KL_TYPE) -> Interval:
        """
        将自定义的KL_TYPE转换为vn.py的Interval类型。
        """
        mapping = {
            KL_TYPE.K_1M: Interval.MINUTE,
            KL_TYPE.K_60M: Interval.HOUR,
            KL_TYPE.K_DAY: Interval.DAILY,
            KL_TYPE.K_WEEK: Interval.WEEKLY,
        }
        if k_type not in mapping:
            raise CChanException(f"不支持的K线类型: {k_type}", ErrCode.COMMON_ERROR)
        return mapping[k_type]
