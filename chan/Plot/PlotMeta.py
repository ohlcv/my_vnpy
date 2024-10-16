from typing import List

from Bi.Bi import CBi
from BuySellPoint.BS_Point import CBS_Point
from Common.CEnum import FX_TYPE
from KLine.KLine import CKLine
from KLine.KLine_List import CKLine_List
from Seg.Eigen import CEigen
from Seg.EigenFX import CEigenFX
from Seg.Seg import CSeg
from ZS.ZS import CZS


class Cklc_meta:
    """K线元数据类，封装K线数据的关键信息。"""
    
    def __init__(self, klc: CKLine):
        self.high = klc.high  # K线的最高价
        self.low = klc.low    # K线的最低价
        self.begin_idx = klc.lst[0].idx  # K线开始的索引
        self.end_idx = klc.lst[-1].idx    # K线结束的索引
        self.type = klc.fx if klc.fx != FX_TYPE.UNKNOWN else klc.dir  # K线的类型

        self.klu_list = list(klc.lst)  # K线的子K线列表


class CBi_meta:
    """笔元数据类，封装笔的关键信息。"""
    
    def __init__(self, bi: CBi):
        self.idx = bi.idx  # 笔的索引
        self.dir = bi.dir  # 笔的方向
        self.type = bi.type  # 笔的类型
        self.begin_x = bi.get_begin_klu().idx  # 笔开始K线的索引
        self.end_x = bi.get_end_klu().idx      # 笔结束K线的索引
        self.begin_y = bi.get_begin_val()      # 笔开始的值
        self.end_y = bi.get_end_val()          # 笔结束的值
        self.id_sure = bi.is_sure              # 笔是否确定


class CSeg_meta:
    """段元数据类，封装段的关键信息。"""
    
    def __init__(self, seg: CSeg):
        # 判断段的起始笔类型，并提取相关信息
        if isinstance(seg.start_bi, CBi):
            self.begin_x = seg.start_bi.get_begin_klu().idx
            self.begin_y = seg.start_bi.get_begin_val()
            self.end_x = seg.end_bi.get_end_klu().idx
            self.end_y = seg.end_bi.get_end_val()
        else:
            assert isinstance(seg.start_bi, CSeg)
            self.begin_x = seg.start_bi.start_bi.get_begin_klu().idx
            self.begin_y = seg.start_bi.start_bi.get_begin_val()
            self.end_x = seg.end_bi.end_bi.get_end_klu().idx
            self.end_y = seg.end_bi.end_bi.get_end_val()

        self.dir = seg.dir  # 段的方向
        self.is_sure = seg.is_sure  # 段是否确定

        # 存储支持和阻力趋势线
        self.tl = {}
        if seg.support_trend_line and seg.support_trend_line.line:
            self.tl["support"] = seg.support_trend_line
        if seg.resistance_trend_line and seg.resistance_trend_line.line:
            self.tl["resistance"] = seg.resistance_trend_line

    def format_tl(self, tl):
        """格式化趋势线的坐标。"""
        assert tl.line
        tl_slope = tl.line.slope + 1e-7  # 避免除零错误
        tl_x = tl.line.p.x
        tl_y = tl.line.p.y
        tl_y0 = self.begin_y
        tl_y1 = self.end_y
        tl_x0 = (tl_y0 - tl_y) / tl_slope + tl_x  # 计算起始点的x坐标
        tl_x1 = (tl_y1 - tl_y) / tl_slope + tl_x  # 计算结束点的x坐标
        return tl_x0, tl_y0, tl_x1, tl_y1


class CEigen_meta:
    """特征元数据类，封装特征的关键信息。"""
    
    def __init__(self, eigen: CEigen):
        self.begin_x = eigen.lst[0].get_begin_klu().idx  # 特征开始K线的索引
        self.end_x = eigen.lst[-1].get_end_klu().idx     # 特征结束K线的索引
        self.begin_y = eigen.low                           # 特征的最低值
        self.end_y = eigen.high                            # 特征的最高值
        self.w = self.end_x - self.begin_x                # 特征的宽度
        self.h = self.end_y - self.begin_y                # 特征的高度


class CEigenFX_meta:
    """特征FX元数据类，封装特征FX的关键信息。"""
    
    def __init__(self, eigenFX: CEigenFX):
        self.ele = [CEigen_meta(ele) for ele in eigenFX.ele if ele is not None]  # 提取特征元数据
        assert len(self.ele) == 3  # 期望有三个元素
        assert eigenFX.ele[1] is not None  # 第二个元素不能为None
        self.gap = eigenFX.ele[1].gap  # 特征间的间隔
        self.fx = eigenFX.ele[1].fx    # 特征的类型


class CZS_meta:
    """走势段元数据类，封装走势段的关键信息。"""
    
    def __init__(self, zs: CZS):
        self.low = zs.low  # 走势段的最低价
        self.high = zs.high  # 走势段的最高价
        self.begin = zs.begin.idx  # 走势段开始的索引
        self.end = zs.end.idx      # 走势段结束的索引
        self.w = self.end - self.begin  # 走势段的宽度
        self.h = self.high - self.low    # 走势段的高度
        self.is_sure = zs.is_sure  # 走势段是否确定
        self.sub_zs_lst = [CZS_meta(t) for t in zs.sub_zs_lst]  # 子走势段列表
        self.is_onebi_zs = zs.is_one_bi_zs()  # 是否为单笔走势段


class CBS_Point_meta:
    """买卖点元数据类，封装买卖点的关键信息。"""
    
    def __init__(self, bsp: CBS_Point, is_seg):
        self.is_buy = bsp.is_buy  # 买卖点是否为买入
        self.type = bsp.type2str()  # 买卖点类型的字符串表示
        self.is_seg = is_seg  # 是否为段内的买卖点

        self.x = bsp.klu.idx  # 买卖点对应的K线索引
        self.y = bsp.klu.low if self.is_buy else bsp.klu.high  # 买卖点的值

    def desc(self):
        """返回买卖点的描述信息。"""
        is_seg_flag = "※" if self.is_seg else ""  # 如果是段内买卖点，添加标记
        return f'{is_seg_flag}b{self.type}' if self.is_buy else f'{is_seg_flag}s{self.type}'


class CChanPlotMeta:
    """通道绘图元数据类，封装绘图所需的K线和相关信息。"""
    
    def __init__(self, kl_list: CKLine_List):
        self.data = kl_list  # 存储传入的K线列表

        # 将每根K线转换为K线元数据列表
        self.klc_list: List[Cklc_meta] = [Cklc_meta(klc) for klc in kl_list.lst]
        # 将每根K线的时间转换为字符串格式，生成时间标记列表
        self.datetick = [klu.time.to_str() for klu in self.klu_iter()]
        # 计算所有K线的子K线总数
        self.klu_len = sum(len(klc.klu_list) for klc in self.klc_list)

        # 提取笔的元数据
        self.bi_list = [CBi_meta(bi) for bi in kl_list.bi_list]
        self.seg_list: List[CSeg_meta] = []  # 段的元数据列表
        self.eigenfx_lst: List[CEigenFX_meta] = []  # 特征FX的元数据列表

        # 提取段的元数据
        for seg in kl_list.seg_list:
            self.seg_list.append(CSeg_meta(seg))  # 添加段的元数据
            if seg.eigen_fx:
                self.eigenfx_lst.append(CEigenFX_meta(seg.eigen_fx))  # 如果存在特征FX，则添加

        # 提取段段和走势段的元数据
        self.segseg_list: List[CSeg_meta] = [CSeg_meta(segseg) for segseg in kl_list.segseg_list]
        self.zs_lst: List[CZS_meta] = [CZS_meta(zs) for zs in kl_list.zs_list]  # 走势段的元数据
        self.segzs_lst: List[CZS_meta] = [CZS_meta(segzs) for segzs in kl_list.segzs_list]  # 段走势段的元数据

        # 提取买卖点的元数据
        self.bs_point_lst: List[CBS_Point_meta] = [CBS_Point_meta(bs_point, is_seg=False) for bs_point in kl_list.bs_point_lst]
        self.seg_bsp_lst: List[CBS_Point_meta] = [CBS_Point_meta(seg_bsp, is_seg=True) for seg_bsp in kl_list.seg_bs_point_lst]

    def klu_iter(self):
        """迭代器，生成每根K线的子K线索引。"""
        for klc in self.klc_list:
            yield from klc.klu_list  # 逐个生成子K线

    def sub_last_kseg_start_idx(self, seg_cnt):
        """获取指定数量的最后一个段的起始K线索引。"""
        if seg_cnt is None or len(self.data.seg_list) <= seg_cnt:
            return 0  # 如果段数无效，则返回0
        else:
            # 返回指定段数的最后一个段的起始K线索引
            return self.data.seg_list[-seg_cnt].get_begin_klu().sub_kl_list[0].idx

    def sub_last_kbi_start_idx(self, bi_cnt):
        """获取指定数量的最后一个笔的起始K线索引。"""
        if bi_cnt is None or len(self.data.bi_list) <= bi_cnt:
            return 0  # 如果笔数无效，则返回0
        else:
            # 返回指定笔数的最后一个笔的起始K线索引
            return self.data.bi_list[-bi_cnt].begin_klc.lst[0].sub_kl_list[0].idx

    def sub_range_start_idx(self, x_range):
        """根据范围获取起始K线索引。"""
        for klc in self.data[::-1]:  # 从最后一根K线开始遍历
            for klu in klc[::-1]:  # 从子K线列表的最后一根开始遍历
                x_range -= 1  # 减少范围计数
                if x_range == 0:
                    return klu.sub_kl_list[0].idx  # 返回当前K线的起始索引
        return 0  # 如果没有找到，返回0

