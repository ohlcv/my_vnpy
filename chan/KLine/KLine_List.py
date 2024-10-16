import copy
from typing import List, Union, overload

from ..Bi.Bi import CBi
from ..Bi.BiList import CBiList
from ..BuySellPoint.BSPointList import CBSPointList
from ..ChanConfig import CChanConfig
from ..Common.CEnum import KLINE_DIR, SEG_TYPE
from ..Common.ChanException import CChanException, ErrCode
from ..Seg.Seg import CSeg
from ..Seg.SegConfig import CSegConfig
from ..Seg.SegListComm import CSegListComm
from ..ZS.ZSList import CZSList

from .KLine import CKLine
from .KLine_Unit import CKLine_Unit


def get_seglist_instance(seg_config: CSegConfig, lv) -> CSegListComm:
    """根据分段算法类型返回相应的分段列表实例。
    
    Args:
        seg_config (CSegConfig): 分段配置对象。
        lv: 分段类型。
    
    Returns:
        CSegListComm: 分段列表实例。
    
    Raises:
        CChanException: 如果分段算法不被支持，抛出异常。
    """
    if seg_config.seg_algo == "chan":
        from ..Seg.SegListChan import CSegListChan
        return CSegListChan(seg_config, lv)
    elif seg_config.seg_algo == "1+1":
        print(f'Please avoid using seg_algo={seg_config.seg_algo} as it is deprecated and no longer maintained.')
        from ..Seg.SegListDYH import CSegListDYH
        return CSegListDYH(seg_config, lv)
    elif seg_config.seg_algo == "break":
        print(f'Please avoid using seg_algo={seg_config.seg_algo} as it is deprecated and no longer maintained.')
        from ..Seg.SegListDef import CSegListDef
        return CSegListDef(seg_config, lv)
    else:
        raise CChanException(f"unsupport seg algoright:{seg_config.seg_algo}", ErrCode.PARA_ERROR)


class CKLine_List:
    """K线列表类，用于管理和处理K线数据及相关计算。
    
    Attributes:
        kl_type: K线类型。
        config: 策略配置对象。
        lst: 存储K线的列表。
        bi_list: 存储笔的列表。
        seg_list: 存储线段的列表。
        segseg_list: 存储线段的线段列表。
        zs_list: 存储中枢的列表。
        segzs_list: 存储线段的中枢列表。
        bs_point_lst: 存储买卖点列表。
        seg_bs_point_lst: 存储线段的买卖点列表。
        metric_model_lst: 指标模型列表。
        step_calculation: 是否需要逐步计算。
    """

    def __init__(self, kl_type, conf: CChanConfig):
        """初始化K线列表实例。
        
        Args:
            kl_type: K线类型。
            conf (CChanConfig): 策略配置对象。
        """
        self.kl_type = kl_type
        self.config = conf
        self.lst: List[CKLine] = []  # K线列表，元素为CKLine类型
        self.bi_list = CBiList(bi_conf=conf.bi_conf)  # 笔的列表
        self.seg_list: CSegListComm[CBi] = get_seglist_instance(seg_config=conf.seg_conf, lv=SEG_TYPE.BI)  # 线段列表
        self.segseg_list: CSegListComm[CSeg[CBi]] = get_seglist_instance(seg_config=conf.seg_conf, lv=SEG_TYPE.SEG)  # 线段的线段列表

        self.zs_list = CZSList(zs_config=conf.zs_conf)  # 中枢列表
        self.segzs_list = CZSList(zs_config=conf.zs_conf)  # 线段的中枢列表

        self.bs_point_lst = CBSPointList[CBi, CBiList](bs_point_config=conf.bs_point_conf)  # 买卖点列表
        self.seg_bs_point_lst = CBSPointList[CSeg, CSegListComm](bs_point_config=conf.seg_bs_point_conf)  # 线段的买卖点列表

        self.metric_model_lst = conf.GetMetricModel()  # 指标模型列表

        self.step_calculation = self.need_cal_step_by_step()  # 是否需要逐步计算

    def __deepcopy__(self, memo):
        """实现深拷贝方法，用于复制K线列表实例及其相关数据。
        
        Args:
            memo: 用于存储已拷贝对象的字典。
        
        Returns:
            new_obj: 新的K线列表实例。
        """
        new_obj = CKLine_List(self.kl_type, self.config)
        memo[id(self)] = new_obj
        for klc in self.lst:
            klus_new = []
            for klu in klc.lst:
                new_klu = copy.deepcopy(klu, memo)  # 深拷贝K线单元
                memo[id(klu)] = new_klu
                if klu.pre is not None:
                    new_klu.set_pre_klu(memo[id(klu.pre)])  # 设置前一根K线单元
                klus_new.append(new_klu)

            new_klc = CKLine(klus_new[0], idx=klc.idx, _dir=klc.dir)  # 创建新的K线
            new_klc.set_fx(klc.fx)  # 设置分型
            new_klc.kl_type = klc.kl_type  # 设置K线类型
            for idx, klu in enumerate(klus_new):
                klu.set_klc(new_klc)  # 设置当前K线单元的K线
                if idx != 0:
                    new_klc.add(klu)  # 添加K线单元到新K线中
            memo[id(klc)] = new_klc  # 存储拷贝的K线对象
            if new_obj.lst:
                new_obj.lst[-1].set_next(new_klc)  # 设置下一根K线
                new_klc.set_pre(new_obj.lst[-1])  # 设置前一根K线
            new_obj.lst.append(new_klc)  # 将新K线添加到列表中
        new_obj.bi_list = copy.deepcopy(self.bi_list, memo)  # 深拷贝笔列表
        new_obj.seg_list = copy.deepcopy(self.seg_list, memo)  # 深拷贝线段列表
        new_obj.segseg_list = copy.deepcopy(self.segseg_list, memo)  # 深拷贝线段的线段列表
        new_obj.zs_list = copy.deepcopy(self.zs_list, memo)  # 深拷贝中枢列表
        new_obj.segzs_list = copy.deepcopy(self.segzs_list, memo)  # 深拷贝线段的中枢列表
        new_obj.bs_point_lst = copy.deepcopy(self.bs_point_lst, memo)  # 深拷贝买卖点列表
        new_obj.metric_model_lst = copy.deepcopy(self.metric_model_lst, memo)  # 深拷贝指标模型列表
        new_obj.step_calculation = copy.deepcopy(self.step_calculation, memo)  # 深拷贝逐步计算标志
        new_obj.seg_bs_point_lst = copy.deepcopy(self.seg_bs_point_lst, memo)  # 深拷贝线段的买卖点列表
        return new_obj

    @overload
    def __getitem__(self, index: int) -> CKLine: ...

    @overload
    def __getitem__(self, index: slice) -> List[CKLine]: ...

    def __getitem__(self, index: Union[slice, int]) -> Union[List[CKLine], CKLine]:
        """获取指定索引的K线或K线列表。
        
        Args:
            index (Union[slice, int]): 索引或切片。
        
        Returns:
            Union[List[CKLine], CKLine]: 指定索引的K线或K线列表。
        """
        return self.lst[index]

    def __len__(self):
        """获取K线列表的长度。
        
        Returns:
            int: K线列表的长度。
        """
        return len(self.lst)

    def cal_seg_and_zs(self):
        """计算线段和中枢（seg和zs）。

        该函数首先检查是否需要虚拟笔（virtual bi），然后依次计算线段和中枢，包括线段中枢和线段线段中枢。
        最后，计算买卖点。

        主要步骤：
        1. 尝试添加虚拟笔。
        2. 计算bi_list中的线段seg。
        3. 计算seg中的中枢。
        4. 更新seg中的中枢信息，包括bi_in和bi_out。
        5. 计算seg中的线段线段。
        6. 计算segseg中的中枢。
        7. 更新segseg中的中枢信息。
        8. 计算线段线段和笔的买卖点。
        """
        if not self.step_calculation:  # 如果不需要逐步计算
            self.bi_list.try_add_virtual_bi(self.lst[-1])  # 尝试添加虚拟笔
        # 计算bi_list的线段seg
        cal_seg(self.bi_list, self.seg_list)
        # 计算bi_list和seg_list的中枢
        self.zs_list.cal_bi_zs(self.bi_list, self.seg_list)
        # 更新bi_list和seg_list中的中枢信息，包括bi_in和bi_out
        update_zs_in_seg(self.bi_list, self.seg_list, self.zs_list)
        # 计算seg_list的线段segseg
        cal_seg(self.seg_list, self.segseg_list)
        # 计算seg_list和segseg_list的中枢
        self.segzs_list.cal_bi_zs(self.seg_list, self.segseg_list)
        # 更新seg_list和segseg_list中的中枢信息
        update_zs_in_seg(self.seg_list, self.segseg_list, self.segzs_list)
        # 计算线段线段的买卖点
        self.seg_bs_point_lst.cal(self.seg_list, self.segseg_list)
        # 计算笔的买卖点
        self.bs_point_lst.cal(self.bi_list, self.seg_list)

    def need_cal_step_by_step(self):
        """判断是否需要逐步计算K线。

        如果配置中触发了逐步计算，则返回True，否则返回False。
        
        Returns:
            bool: 是否触发逐步计算。
        """
        return self.config.trigger_step

    def add_single_klu(self, klu: CKLine_Unit):
        """添加单个K线单元并更新K线、线段及中枢信息。

        当新的K线单元加入时，会计算K线的方向，并根据不同情况决定是否合并K线。
        如果加入的K线形成了新的笔或虚拟笔，会触发线段和中枢的重新计算。

        Args:
            klu (CKLine_Unit): 新加入的K线单元。
        """
        klu.set_metric(self.metric_model_lst)  # 设置指标模型

        # 如果K线列表为空，直接将klu添加为第一根K线
        if len(self.lst) == 0:
            self.lst.append(CKLine(klu, idx=0))
        else:
            _dir = self.lst[-1].try_add(klu)  # 尝试添加klu并判断方向
            if _dir != KLINE_DIR.COMBINE:  # 如果不需要合并K线
                self.lst.append(CKLine(klu, idx=len(self.lst), _dir=_dir))  # 添加新的K线
                
                # 更新K线的分型信息（只在三根或以上K线时进行）
                if len(self.lst) >= 3:
                    self.lst[-2].update_fx(self.lst[-3], self.lst[-1])
                
                # 如果形成了新的笔，触发线段和中枢的重新计算
                if self.bi_list.update_bi(self.lst[-2], self.lst[-1], self.step_calculation) and self.step_calculation:
                    self.cal_seg_and_zs()
            # 如果需要逐步计算，尝试添加虚拟笔，并重新计算线段和中枢
            elif self.step_calculation and self.bi_list.try_add_virtual_bi(self.lst[-1], need_del_end=True):
                self.cal_seg_and_zs()

    def klu_iter(self, klc_begin_idx=0):
        """迭代器，依次返回从klc_begin_idx开始的K线列表中的每个K线单元。

        Args:
            klc_begin_idx (int, optional): 开始迭代的索引。默认为0。
        
        Yields:
            CKLine_Unit: 逐个返回K线单元。
        """
        for klc in self.lst[klc_begin_idx:]:
            yield from klc.lst


def cal_seg(bi_list, seg_list: CSegListComm):
    """计算bi_list中的线段seg。

    根据bi_list的笔更新seg_list的线段，依次为每根笔分配对应的线段索引。

    Args:
        bi_list (list): 笔列表。
        seg_list (CSegListComm): 线段列表。
    """
    seg_list.update(bi_list)  # 更新seg_list的线段信息

    sure_seg_cnt = 0  # 已确认的线段数量
    if len(seg_list) == 0:
        for bi in bi_list:
            bi.set_seg_idx(0)  # 如果没有线段，将所有bi的seg_idx设为0
        return
    
    begin_seg: CSeg = seg_list[-1]  # 从最后一个线段开始
    # 从后往前查找已确认的线段，如果找到超过2个已确认的线段，则停止查找
    for seg in seg_list[::-1]:
        if seg.is_sure:
            sure_seg_cnt += 1
        else:
            sure_seg_cnt = 0
        begin_seg = seg
        if sure_seg_cnt > 2:
            break

    cur_seg: CSeg = seg_list[-1]  # 当前线段
    # 反向遍历bi_list，为每根bi分配对应的seg_idx
    for bi in bi_list[::-1]:
        if bi.seg_idx is not None and bi.idx < begin_seg.start_bi.idx:
            break  # 如果bi的索引小于起始线段的开始索引，停止
        if bi.idx > cur_seg.end_bi.idx:
            bi.set_seg_idx(cur_seg.idx+1)  # 分配新的线段索引
            continue
        if bi.idx < cur_seg.start_bi.idx:
            assert cur_seg.pre  # 确保当前线段有前驱线段
            cur_seg = cur_seg.pre  # 切换到前一个线段
        bi.set_seg_idx(cur_seg.idx)  # 设置当前bi的seg_idx


def update_zs_in_seg(bi_list, seg_list, zs_list):
    """更新seg中的中枢信息。

    遍历seg_list中的线段，检查每个中枢是否在当前线段内部，并更新中枢的bi_in和bi_out信息。

    Args:
        bi_list (list): 笔列表。
        seg_list (list): 线段列表。
        zs_list (list): 中枢列表。
    """
    sure_seg_cnt = 0  # 已确认的线段数量
    for seg in seg_list[::-1]:  # 从后往前遍历线段列表
        if seg.ele_inside_is_sure:
            break  # 如果当前线段的中枢已确认，停止遍历
        if seg.is_sure:
            sure_seg_cnt += 1  # 增加已确认线段计数
        seg.clear_zs_lst()  # 清空线段中的中枢列表
        for zs in zs_list[::-1]:  # 从后往前遍历中枢列表
            if zs.end.idx < seg.start_bi.get_begin_klu().idx:
                break  # 如果中枢的结束索引小于线段的开始索引，停止遍历
            if zs.is_inside(seg):
                seg.add_zs(zs)  # 如果中枢在当前线段内部，添加到线段中
            assert zs.begin_bi.idx > 0  # 确保中枢的开始bi索引大于0
            zs.set_bi_in(bi_list[zs.begin_bi.idx-1])  # 设置中枢的bi_in
            if zs.end_bi.idx+1 < len(bi_list):
                zs.set_bi_out(bi_list[zs.end_bi.idx+1])  # 设置中枢的bi_out
            zs.set_bi_lst(list(bi_list[zs.begin_bi.idx:zs.end_bi.idx+1]))  # 设置中枢内的笔列表

        if sure_seg_cnt > 2:
            if not seg.ele_inside_is_sure:
                seg.ele_inside_is_sure = True  # 如果已确认超过两个线段，标记线段内的中枢为已确认
