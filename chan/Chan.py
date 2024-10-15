import copy
import datetime
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Union

# 从 BuySellPoint 模块导入 CBS_Point 类
from .BuySellPoint.BS_Point import CBS_Point

# 导入 ChanConfig 配置类
from .ChanConfig import CChanConfig

# 从 Common 模块导入各种枚举类型和异常类
from .Common.CEnum import AUTYPE, DATA_SRC, KL_TYPE
from .Common.ChanException import CChanException, ErrCode
from .Common.CTime import CTime
from .Common.func_util import check_kltype_order, kltype_lte_day

# 从 DataAPI 模块导入公共股票 API 类
from .DataAPI.CommonStockAPI import CCommonStockApi

# 从 KLine 模块导入自定义的 K 线列表和 K 线单元类
from .KLine.KLine_List import CKLine_List  # 自定义 K 线列表
from .KLine.KLine_Unit import CKLine_Unit  # 自定义 K 线单元

import importlib


class CChan:
    """
    CChan 类主要用于处理和分析 K 线数据，并根据不同级别的 K 线生成线段、中枢等。

    :param code: 股票代码或交易对符号。
    :param begin_time: 开始时间，可以是字符串或 datetime 类型。
    :param end_time: 结束时间，可以是字符串或 datetime 类型。
    :param data_src: 数据来源（枚举类型），默认为 BAO_STOCK。
    :param lv_list: K 线级别列表，如日线、小时线等，顺序从高到低。
    :param config: CChanConfig 配置对象，用于指定策略配置。
    :param autype: 复权类型（枚举类型），默认为前复权。
    """

    def __init__(
        self,
        code,
        begin_time=None,
        end_time=None,
        data_src: Union[DATA_SRC, str] = DATA_SRC.BAO_STOCK,
        lv_list=None,
        config=None,
        autype: AUTYPE = AUTYPE.QFQ,
    ):
        # 默认 K 线级别为日线和60分钟线
        if lv_list is None:
            lv_list = [KL_TYPE.K_DAY, KL_TYPE.K_60M]

        # 检查 K 线级别顺序是否从高到低排列
        check_kltype_order(lv_list)

        # 初始化基本属性
        self.code = code  # 股票代码或交易对符号
        self.begin_time = (
            str(begin_time) if isinstance(begin_time, datetime.date) else begin_time
        )
        self.end_time = (
            str(end_time) if isinstance(end_time, datetime.date) else end_time
        )
        self.autype = autype  # 复权类型
        self.data_src = data_src  # 数据来源
        self.lv_list: List[KL_TYPE] = lv_list  # K 线级别列表

        # 如果配置为空，则使用默认配置 CChanConfig
        if config is None:
            config = CChanConfig()
        self.conf = config

        # 初始化 K 线不对齐的次数计数和不一致的详细信息
        self.kl_misalign_cnt = 0  # K 线不对齐的次数计数
        self.kl_inconsistent_detail = defaultdict(list)  # K 线不一致的详细信息

        # 初始化 K 线数据迭代器，按级别存储
        self.g_kl_iter = defaultdict(list)

        # 执行初始化 K 线数据的方法
        self.do_init()

        # 非触发模式下，立即加载数据
        if not config.trigger_step:
            for _ in self.load():
                ...

    def __deepcopy__(self, memo):
        """
        实现对象深拷贝的逻辑。
        主要拷贝对象中各级别的 K 线数据和其他属性，并保持子父关系的一致性。
        """
        cls = self.__class__
        obj: CChan = cls.__new__(cls)  # 创建一个新的 CChan 对象
        memo[id(self)] = obj  # 记录当前对象的拷贝

        # 复制基本属性
        obj.code = self.code
        obj.begin_time = self.begin_time
        obj.end_time = self.end_time
        obj.autype = self.autype
        obj.data_src = self.data_src
        obj.lv_list = copy.deepcopy(self.lv_list, memo)
        obj.conf = copy.deepcopy(self.conf, memo)
        obj.kl_misalign_cnt = self.kl_misalign_cnt
        obj.kl_inconsistent_detail = copy.deepcopy(self.kl_inconsistent_detail, memo)
        obj.g_kl_iter = copy.deepcopy(self.g_kl_iter, memo)

        # 拷贝属性 klu_cache 和 klu_last_t（如果存在）
        if hasattr(self, "klu_cache"):
            obj.klu_cache = copy.deepcopy(self.klu_cache, memo)
        if hasattr(self, "klu_last_t"):
            obj.klu_last_t = copy.deepcopy(self.klu_last_t, memo)

        # 深拷贝 K 线数据并保持子父关系
        obj.kl_datas = {}
        for kl_type, ckline in self.kl_datas.items():
            obj.kl_datas[kl_type] = copy.deepcopy(ckline, memo)
        for kl_type, ckline in self.kl_datas.items():
            for klc in ckline:
                for klu in klc.lst:
                    assert id(klu) in memo
                    if klu.sup_kl:
                        memo[id(klu)].sup_kl = memo[id(klu.sup_kl)]
                    memo[id(klu)].sub_kl_list = [
                        memo[id(sub_kl)] for sub_kl in klu.sub_kl_list
                    ]
        return obj

    def do_init(self):
        """
        初始化 K 线数据字典 `kl_datas`。
        每个级别的 K 线列表对象（CKLine_List）将根据传入的 K 线级别列表 `lv_list` 创建。
        """
        self.kl_datas: Dict[KL_TYPE, CKLine_List] = {}
        for idx in range(len(self.lv_list)):
            self.kl_datas[self.lv_list[idx]] = CKLine_List(
                self.lv_list[idx], conf=self.conf
            )

    def load_stock_data(
        self, stockapi_instance: CCommonStockApi, lv
    ) -> Iterable[CKLine_Unit]:
        """
        根据股票 API 实例 `stockapi_instance` 和指定级别 `lv`，逐个生成 K 线单元 `CKLine_Unit`。

        :param stockapi_instance: 数据 API 实例。
        :param lv: 指定 K 线级别。
        :return: 生成器，逐个返回 K 线单元。
        """
        for KLU_IDX, klu in enumerate(stockapi_instance.get_kl_data()):
            klu.set_idx(KLU_IDX)  # 设置 K 线单元的索引
            klu.kl_type = lv  # 设置 K 线级别
            yield klu  # 逐个返回 K 线单元

    def get_load_stock_iter(self, stockapi_cls, lv):
        """
        根据传入的股票 API 类和级别 lv，创建股票数据的迭代器。

        Args:
            stockapi_cls: 股票 API 类，用于获取股票数据。
            lv: 当前股票数据级别（如日线、60分钟线）。

        Returns:
            股票数据的迭代器。
        """
        # 创建股票 API 实例，指定股票代码、K 线类型、起始和结束日期、复权类型等参数
        stockapi_instance = stockapi_cls(
            code=self.code,
            k_type=lv,
            begin_time=self.begin_time,
            end_time=self.end_time,
            autype=self.autype,
        )
        # 调用 load_stock_data 方法，返回股票数据迭代器
        return self.load_stock_data(stockapi_instance, lv)

    def add_lv_iter(self, lv_idx, iter):
        """
        添加股票数据迭代器到 `g_kl_iter` 字典中。

        Args:
            lv_idx: 级别索引或级别类型。如果是整数表示索引，否则表示类型。
            iter: 需要添加的股票数据迭代器。
        """
        # 如果 lv_idx 是整数类型，则使用 lv_list 中的对应级别类型将迭代器添加到 g_kl_iter 中
        if isinstance(lv_idx, int):
            self.g_kl_iter[self.lv_list[lv_idx]].append(iter)
        # 如果 lv_idx 不是整数类型（可能直接传入 KL_TYPE），直接在 g_kl_iter 中添加迭代器
        else:
            self.g_kl_iter[lv_idx].append(iter)

    def get_next_lv_klu(self, lv_idx):
        """
        获取下一个级别的 K 线数据单元 (CKLine_Unit)。

        Args:
            lv_idx: 级别索引或级别类型。

        Returns:
            CKLine_Unit: 下一个 K 线数据单元。

        Raises:
            StopIteration: 如果该级别的数据迭代器已无更多数据。
        """
        # 如果 lv_idx 是整数类型，则转换为对应的级别类型（KL_TYPE）
        if isinstance(lv_idx, int):
            lv_idx = self.lv_list[lv_idx]

        # 检查当前级别的迭代器是否存在并且有数据可供迭代
        if len(self.g_kl_iter[lv_idx]) == 0:
            raise StopIteration

        try:
            # 获取当前迭代器的下一个 K 线单元（可能抛出 StopIteration 异常）
            return self.g_kl_iter[lv_idx][0].__next__()
        except StopIteration:
            # 当前迭代器已结束，从迭代器列表中移除第一个迭代器
            self.g_kl_iter[lv_idx] = self.g_kl_iter[lv_idx][1:]

            # 如果还有其他迭代器，递归调用自身获取下一个 K 线单元
            if len(self.g_kl_iter[lv_idx]) != 0:
                return self.get_next_lv_klu(lv_idx)
            else:
                # 如果所有迭代器都没有数据，抛出 StopIteration 异常
                raise

    def step_load(self):
        """
        按步长加载数据，根据配置的 `trigger_step` 逐步返回快照。

        1. 检查是否设置了 `trigger_step`。
        2. 调用 `do_init` 方法清空已有数据，防止重复加载时数据残留。
        3. 遍历加载的快照，并根据 `skip_step` 跳过指定步数的快照。
        4. 返回加载的快照。如果未加载任何快照，则返回自身对象。

        Yields:
            加载的快照，或自身对象（无数据时）。
        """
        assert self.conf.trigger_step  # 确保触发步长配置已设置
        self.do_init()  # 清空数据，防止数据残留影响重跑结果
        yielded = False  # 标记是否曾经返回过结果

        # 遍历按 `trigger_step` 加载的快照数据
        for idx, snapshot in enumerate(self.load(self.conf.trigger_step)):
            if idx < self.conf.skip_step:  # 跳过指定步数的快照
                continue
            yield snapshot
            yielded = True  # 已返回至少一个快照

        # 如果没有任何快照数据，则返回当前对象自身
        if not yielded:
            yield self

    def trigger_load(self, inp):
        """
        根据输入的多级别 K 线数据，触发级别数据的加载和处理。

        Args:
            inp: 输入的数据字典，键为 K 线级别（如日线、周线等），值为对应级别的 CKLine_Unit 列表。

        Raises:
            CChanException: 当最高级别 lv 的数据没有传入时，抛出异常。
        """
        # 初始化 `klu_cache` 和 `klu_last_t` 属性，用于缓存 CKLine_Unit 和记录最后时间点
        if not hasattr(self, "klu_cache"):
            # 创建与 lv_list 长度相同的 `klu_cache` 列表，每个级别的初始值为 None
            self.klu_cache: List[Optional[CKLine_Unit]] = [None for _ in self.lv_list]
        if not hasattr(self, "klu_last_t"):
            # 创建与 lv_list 长度相同的 `klu_last_t` 列表，每个级别的初始时间点为 1980-01-01 00:00
            self.klu_last_t = [CTime(1980, 1, 1, 0, 0) for _ in self.lv_list]

        # 遍历每个 K 线级别，根据输入数据将其转换为迭代器并存入 `g_kl_iter` 中
        for lv_idx, lv in enumerate(self.lv_list):
            if lv not in inp:  # 如果当前级别没有数据
                if lv_idx == 0:  # 如果是最高级别没有数据，则抛出异常
                    raise CChanException(f"最高级别{lv}没有传入数据", ErrCode.NO_DATA)
                continue

            # 设置当前级别的 klu 对象的类型属性
            for klu in inp[lv]:
                klu.kl_type = lv
            assert isinstance(inp[lv], list)  # 确保输入的数据为列表类型

            # 将输入数据转换为迭代器并添加到 `g_kl_iter` 字典中
            self.add_lv_iter(lv, iter(inp[lv]))

        # 加载最高级别数据，执行迭代器进行数据处理（如计算线段、中枢）
        for _ in self.load_iterator(lv_idx=0, parent_klu=None, step=False):
            ...

        # 如果未启用 `trigger_step`（非回放模式），则计算所有级别的线段和中枢
        if not self.conf.trigger_step:
            for lv in self.lv_list:
                self.kl_datas[lv].cal_seg_and_zs()  # 计算线段和中枢

    def init_lv_klu_iter(self, stockapi_cls):
        """
        初始化各级别的 K 线数据迭代器。

        为了跳过某些无法获取数据的级别，将这些级别从有效级别列表中移除。

        Args:
            stockapi_cls: 股票 API 类，用于获取各级别的 K 线数据。

        Returns:
            lv_klu_iter: 有效级别的 K 线数据迭代器列表。
        """
        lv_klu_iter = []  # 存储各有效级别的 K 线数据迭代器
        valid_lv_list = []  # 存储有效的级别

        # 遍历每个级别，尝试获取对应级别的 K 线数据
        for lv in self.lv_list:
            try:
                # 创建该级别的 K 线数据迭代器并添加到列表中
                lv_klu_iter.append(self.get_load_stock_iter(stockapi_cls, lv))
                valid_lv_list.append(lv)
            except CChanException as e:
                # 当数据源找不到时，根据配置决定是否跳过该级别
                if (
                    e.errcode == ErrCode.SRC_DATA_NOT_FOUND
                    and self.conf.auto_skip_illegal_sub_lv
                ):
                    if self.conf.print_warning:
                        print(f"[WARNING-{self.code}]{lv}级别获取数据失败，跳过")
                    del self.kl_datas[lv]  # 从数据字典中移除该级别的数据
                    continue
                raise e  # 其他异常抛出

        # 更新有效的级别列表
        self.lv_list = valid_lv_list
        return lv_klu_iter  # 返回有效级别的迭代器列表

    def GetStockAPI(self):
        """
        根据数据源类型返回相应的股票 API 类。

        根据 `self.data_src` 的值，动态导入对应的数据 API 类并返回。支持以下数据源类型：
        - BAO_STOCK: 导入 `CBaoStock`
        - CCXT: 导入 `CCXT`
        - CSV: 导入 `CSV_API`

        如果 `self.data_src` 以 "custom:" 开头，则动态导入自定义模块和类。

        Returns:
            股票 API 类：对应于当前数据源类型的类。

        Raises:
            CChanException: 如果数据源类型无效或无法加载时，抛出异常。
        """
        _dict = {}  # 存储数据源到类的映射
        if self.data_src == DATA_SRC.BAO_STOCK:
            from DataAPI.BaoStockAPI import CBaoStock

            _dict[DATA_SRC.BAO_STOCK] = CBaoStock
        elif self.data_src == DATA_SRC.CCXT:
            from DataAPI.ccxt import CCXT

            _dict[DATA_SRC.CCXT] = CCXT
        elif self.data_src == DATA_SRC.CSV:
            from DataAPI.csvAPI import CSV_API

            _dict[DATA_SRC.CSV] = CSV_API

        # 如果数据源在映射字典中，返回对应的类
        if self.data_src in _dict:
            return _dict[self.data_src]

        assert isinstance(self.data_src, str)  # 确保数据源类型为字符串

        # 如果数据源不包含 "custom:"，抛出数据源类型错误
        if self.data_src.find("custom:") < 0:
            raise CChanException("load src type error", ErrCode.SRC_DATA_TYPE_ERR)

        # 解析自定义模块和类名称，并导入
        # package_info = self.data_src.split(":")[1]
        # package_name, cls_name = package_info.split(".")
        # exec(f"from DataAPI.{package_name} import {cls_name}")  # 动态导入模块
        # return eval(cls_name)  # 返回对应的类
    
        # 从数据源字符串中提取包信息
        package_info = self.data_src.split(":")[1]  # 以冒号为分隔符，获取数据源的包信息部分
        # 将包信息分解为包名称和类名称
        package_name, cls_name = package_info.split(".")  # 以点号为分隔符，获取模块名称和类名称
        # 动态导入指定的数据 API 模块
        module = importlib.import_module(f".DataAPI.{package_name}", package=__package__)  
        # 使用 importlib 动态导入 DataAPI 目录下指定的模块，`..`表示上级目录，`package=__package__`确保包的上下文正确
        # 获取模块中指定名称的类
        cls = getattr(module, cls_name)  # 从导入的模块中获取指定的类
        # 返回该类
        return cls  # 返回动态导入的类以供后续使用

    def load(self, step=False):
        """
        加载数据，初始化并返回 K 线数据的迭代器。

        1. 获取股票 API 类，并初始化。
        2. 初始化 K 线数据的迭代器，并将其添加到 `g_kl_iter`。
        3. 初始化 K 线缓存和最后时间记录。
        4. 调用 `load_iterator` 计算入口并返回数据。
        5. 如果非回放模式，计算各级别的线段和中枢。

        Args:
            step: 是否以步长模式加载数据，默认为 False。

        Yields:
            K 线数据的快照迭代器。

        Raises:
            CChanException: 当未获取到最高级别数据时，抛出异常。
        """
        if self.begin_time == None:
            return
        
        stockapi_cls = self.GetStockAPI()  # 获取对应的数据 API 类
        try:
            stockapi_cls.do_init()  # 初始化股票 API

            # 初始化各级别的 K 线数据迭代器
            for lv_idx, klu_iter in enumerate(self.init_lv_klu_iter(stockapi_cls)):
                self.add_lv_iter(lv_idx, klu_iter)  # 将迭代器添加到 g_kl_iter

            # 初始化 K 线缓存和最后时间点
            self.klu_cache: List[Optional[CKLine_Unit]] = [None for _ in self.lv_list]
            self.klu_last_t = [CTime(1980, 1, 1, 0, 0) for _ in self.lv_list]

            # 计算入口并返回 K 线数据的快照
            yield from self.load_iterator(lv_idx=0, parent_klu=None, step=step)

            # 如果非回放模式，计算所有级别的线段和中枢
            if not step:
                for lv in self.lv_list:
                    self.kl_datas[lv].cal_seg_and_zs()  # 计算线段和中枢
        except Exception:
            raise  # 抛出捕获的异常
        finally:
            stockapi_cls.do_close()  # 关闭股票 API

        # 检查是否成功获取到最高级别的数据
        if len(self[0]) == 0:
            raise CChanException(
                "最高级别没有获得任何数据", ErrCode.NO_DATA
            )  # 抛出异常

    def set_klu_parent_relation(self, parent_klu, kline_unit, cur_lv, lv_idx):
        """
        设置 K 线单位与其父级 K 线单位的关系，并进行一致性检查（如需要）。

        Args:
            parent_klu: 父级 K 线单位。
            kline_unit: 当前 K 线单位。
            cur_lv: 当前 K 线单位的级别类型。
            lv_idx: 当前级别在级别列表中的索引。
        """
        if (
            self.conf.kl_data_check  # 检查是否启用了数据检查
            and kltype_lte_day(cur_lv)  # 当前级别是否为天级别或以下
            and kltype_lte_day(self.lv_list[lv_idx - 1])  # 上级别是否为天级别或以下
        ):
            self.check_kl_consitent(parent_klu, kline_unit)  # 检查一致性
        parent_klu.add_children(kline_unit)  # 将当前 K 线单位添加为子级
        kline_unit.set_parent(parent_klu)  # 设置父级 K 线单位

    def add_new_kl(self, cur_lv: KL_TYPE, kline_unit):
        """
        向指定级别的数据结构中添加新的 K 线单位。

        Args:
            cur_lv: 当前 K 线单位的级别类型。
            kline_unit: 要添加的 K 线单位。

        Raises:
            Exception: 在添加 K 线单位时发生错误时，抛出异常。

        逻辑:
            - 尝试将新的 K 线单位添加到指定级别的 K 线数据结构中。
            - 如果发生错误，打印错误信息并重新抛出异常。
        """
        try:
            self.kl_datas[cur_lv].add_single_klu(kline_unit)  # 添加新的 K 线单位
        except Exception:
            if self.conf.print_err_time:  # 检查是否启用错误时间打印
                print(
                    f"[ERROR-{self.code}]在计算{kline_unit.time}K线时发生错误!"
                )  # 打印错误信息
            raise  # 抛出异常

    def try_set_klu_idx(self, lv_idx: int, kline_unit: CKLine_Unit):
        """
        尝试设置 K 线单位的索引值。

        Args:
            lv_idx: 当前级别在级别列表中的索引。
            kline_unit: 要设置索引的 K 线单位。

        逻辑:
            - 如果 K 线单位的索引已经被设置为非负值，则返回。
            - 如果当前级别的 K 线数据列表为空，则将索引设置为 0。
            - 否则，将索引设置为当前 K 线单位在列表中的最后一个索引加 1。
        """
        if kline_unit.idx >= 0:  # 如果索引已设置
            return
        if len(self[lv_idx]) == 0:  # 如果当前级别的 K 线数据列表为空
            kline_unit.set_idx(0)  # 设置索引为 0
        else:
            kline_unit.set_idx(
                self[lv_idx][-1][-1].idx + 1
            )  # 设置索引为最后一个 K 线单位的索引 + 1

    def load_iterator(self, lv_idx, parent_klu, step):
        """
        迭代加载 K 线数据。根据 K 线级别的不同，处理不同的时间表示方式。

        Args:
            lv_idx: 当前级别在级别列表中的索引。
            parent_klu: 当前 K 线单位的父级 K 线单位。
            step: 控制迭代行为的参数。

        逻辑:
            - 根据 K 线级别的不同，处理时间信息。
            - 通过循环不断获取新的 K 线单位，添加到数据结构中，并建立层级关系。
            - 当到达上级 K 线单位时间时，停止加载。
        """
        # 获取当前 K 线级别
        cur_lv = self.lv_list[lv_idx]
        # 获取上一个 K 线单位，如果存在的话
        pre_klu = (
            self[lv_idx][-1][-1]  # 获取当前级别最后一根 K 线单位
            if len(self.lv_list) > 0
            and len(self[lv_idx]) > 0
            and len(self[lv_idx][-1]) > 0
            else None
        )

        while True:
            # 如果缓存中有 K 线单位，则直接使用
            if self.klu_cache[lv_idx]:
                kline_unit = self.klu_cache[lv_idx]
                assert kline_unit is not None  # 确保缓存中的 K 线单位不为空
                self.klu_cache[lv_idx] = None  # 清空缓存
            else:
                try:
                    # 从迭代器获取下一个 K 线单位
                    kline_unit = self.get_next_lv_klu(lv_idx)
                    self.try_set_klu_idx(lv_idx, kline_unit)  # 尝试设置 K 线单位的索引
                    # 检查 K 线时间是否单调
                    if not kline_unit.time > self.klu_last_t[lv_idx]:
                        raise CChanException(
                            f"kline time err, cur={kline_unit.time}, last={self.klu_last_t[lv_idx]}",
                            ErrCode.KL_NOT_MONOTONOUS,  # 抛出时间不单调的异常
                        )
                    self.klu_last_t[lv_idx] = kline_unit.time  # 更新最后时间
                except StopIteration:
                    break  # 如果没有更多 K 线单位，则退出循环

            # 如果当前 K 线单位的时间大于父级 K 线单位的时间，则缓存该 K 线单位并退出
            if parent_klu and kline_unit.time > parent_klu.time:
                self.klu_cache[lv_idx] = kline_unit
                break

            kline_unit.set_pre_klu(pre_klu)  # 设置当前 K 线单位的前一个单位
            pre_klu = kline_unit  # 更新前一个 K 线单位
            self.add_new_kl(cur_lv, kline_unit)  # 将当前 K 线单位添加到数据结构中

            # 如果存在父级 K 线单位，建立父子关系
            if parent_klu:
                self.set_klu_parent_relation(parent_klu, kline_unit, cur_lv, lv_idx)

            # 如果不是最后一个级别，递归加载下一个级别的数据
            if lv_idx != len(self.lv_list) - 1:
                for _ in self.load_iterator(lv_idx + 1, kline_unit, step):
                    ...
                self.check_kl_align(kline_unit, lv_idx)  # 检查 K 线单位的对齐

            # 如果是最高级别并且处于步骤模式，生成当前状态
            if lv_idx == 0 and step:
                yield self

    def check_kl_consitent(self, parent_klu, sub_klu):
        """
        检查父级 K 线和子级 K 线的时间是否一致。

        Args:
            parent_klu: 父级 K 线单位。
            sub_klu: 子级 K 线单位。

        如果父级和子级的时间不一致，则记录不一致的信息，并在需要时抛出异常。
        """
        if (
            parent_klu.time.year != sub_klu.time.year
            or parent_klu.time.month != sub_klu.time.month
            or parent_klu.time.day != sub_klu.time.day
        ):
            # 记录不一致的详细信息
            self.kl_inconsistent_detail[str(parent_klu.time)].append(sub_klu.time)
            if self.conf.print_warning:
                print(
                    f"[WARNING-{self.code}]父级别时间是{parent_klu.time}，次级别时间却是{sub_klu.time}"
                )
            # 如果不一致的条目数超过最大限制，抛出异常
            if len(self.kl_inconsistent_detail) >= self.conf.max_kl_inconsistent_cnt:
                raise CChanException(
                    f"父&子级别K线时间不一致条数超过{self.conf.max_kl_inconsistent_cnt}！！",
                    ErrCode.KL_TIME_INCONSISTENT,
                )

    def check_kl_align(self, kline_unit, lv_idx):
        """
        检查 K 线单位与其子级 K 线的对齐情况。

        Args:
            kline_unit: 当前 K 线单位。
            lv_idx: 当前 K 线级别的索引。

        如果当前 K 线单位没有找到子级 K 线，则增加不对齐计数，并在需要时抛出异常。
        """
        if self.conf.kl_data_check and len(kline_unit.sub_kl_list) == 0:
            self.kl_misalign_cnt += 1  # 增加不对齐计数
            if self.conf.print_warning:
                print(
                    f"[WARNING-{self.code}]当前{kline_unit.time}没在次级别{self.lv_list[lv_idx+1]}找到K线！！"
                )
            # 如果不对齐的计数超过最大限制，抛出异常
            if self.kl_misalign_cnt >= self.conf.max_kl_misalgin_cnt:
                raise CChanException(
                    f"在次级别找不到K线条数超过{self.conf.max_kl_misalgin_cnt}！！",
                    ErrCode.KL_DATA_NOT_ALIGN,
                )

    def __getitem__(self, n) -> CKLine_List:
        """
        通过索引访问 K 线数据。

        Args:
            n: 可以是 K 线类型或索引。

        Returns:
            返回对应 K 线类型或索引的 K 线列表。

        Raises:
            CChanException: 如果索引类型不支持，抛出异常。
        """
        if isinstance(n, KL_TYPE):
            return self.kl_datas[n]  # 如果是 K 线类型，返回对应的数据
        elif isinstance(n, int):
            return self.kl_datas[self.lv_list[n]]  # 如果是整数索引，返回对应的 K 线数据
        else:
            raise CChanException("unspoourt query type", ErrCode.COMMON_ERROR)

    def get_bsp(self, idx=None) -> List[CBS_Point]:
        """
        获取买卖点（BSP）。

        Args:
            idx: 可选，指定 K 线级别的索引。

        Returns:
            返回按时间排序的买卖点列表。

        如果没有提供索引，则默认返回最高级别的 BSP。
        """
        if idx is not None:
            # 根据给定索引返回排序后的 BSP 列表
            return sorted(self[idx].bs_point_lst.lst, key=lambda x: x.klu.time)
        assert len(self.lv_list) == 1  # 确保只有一个级别
        # 默认返回最高级别的 BSP 列表
        return sorted(self[0].bs_point_lst.lst, key=lambda x: x.klu.time)
