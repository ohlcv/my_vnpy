import abc
from typing import Iterable

from ..KLine.KLine_Unit import CKLine_Unit


class CCommonStockApi:
    def __init__(self, code, k_type, begin_time, end_time, autype):
        self.code = code
        self.name = None
        self.is_stock = None
        self.k_type = k_type
        self.begin_time = begin_time
        self.end_time = end_time
        self.autype = autype
        self.SetBasciInfo()

    @abc.abstractmethod
    def get_kl_data(self) -> Iterable[CKLine_Unit]:
        pass

    @abc.abstractmethod
    def SetBasciInfo(self):
        pass

    @classmethod
    @abc.abstractmethod
    def do_init(cls):
        pass

    @classmethod
    @abc.abstractmethod
    def do_close(cls):
        pass
