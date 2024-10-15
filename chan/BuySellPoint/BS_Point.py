from typing import Dict, Generic, List, Optional, TypeVar, Union

# 导入必要的类和枚举
from ..Bi.Bi import CBi  # 表示走势段或笔的类
from ..ChanModel.Features import CFeatures  # 特征类，用于管理买卖点的特征
from ..Common.CEnum import BSP_TYPE  # 表示买卖点类型的枚举
from ..Seg.Seg import CSeg  # 表示分段的类

# 声明泛型变量，LINE_TYPE可以是CBi或CSeg类型
LINE_TYPE = TypeVar("LINE_TYPE", CBi, CSeg)


# 定义CBS_Point类，表示买卖点
class CBS_Point(Generic[LINE_TYPE]):
    def __init__(
        self,
        bi: LINE_TYPE,
        is_buy,
        bs_type: BSP_TYPE,
        relate_bsp1: Optional["CBS_Point"],
        feature_dict=None,
    ):
        """
        初始化一个CBS_Point对象，表示买卖点。

        参数：
        bi: 走势段或分段，用于定义该买卖点所处的段
        is_buy: 表示买卖点是买入还是卖出
        bs_type: 当前买卖点的类型
        relate_bsp1: 相关的另一个买卖点
        feature_dict: 特征字典，用于初始化该买卖点的特征
        """
        self.bi: LINE_TYPE = bi  # 定义该买卖点所属的走势段或分段
        self.klu = bi.get_end_klu()  # 获取走势段或分段的结束点
        self.is_buy = is_buy  # 标识是否为买入点
        self.type: List[BSP_TYPE] = [bs_type]  # 买卖点的类型，使用列表存储
        self.relate_bsp1 = relate_bsp1  # 关联的另一个买卖点

        # 将买卖点与对应的走势段或分段关联
        self.bi.bsp = self  # type: ignore 忽略类型检查

        # 初始化特征
        self.features = CFeatures(feature_dict)

        # 标识是否为分段买卖点
        self.is_segbsp = False

        # 初始化通用特征
        self.init_common_feature()

    def add_type(self, bs_type: BSP_TYPE):
        """
        添加买卖点类型。

        参数：
        bs_type: 需要添加的买卖点类型
        """
        self.type.append(bs_type)

    def type2str(self):
        """
        将买卖点类型列表转换为字符串，方便输出和查看。

        返回：
        str: 用逗号分隔的买卖点类型字符串
        """
        return ",".join([x.value for x in self.type])

    def add_another_bsp_prop(self, bs_type: BSP_TYPE, relate_bsp1):
        """
        为买卖点添加另一种属性，并关联另一个买卖点。

        参数：
        bs_type: 要添加的买卖点类型
        relate_bsp1: 要关联的另一个买卖点
        """
        self.add_type(bs_type)
        if self.relate_bsp1 is None:
            self.relate_bsp1 = relate_bsp1  # 如果当前没有关联的买卖点，则进行关联
        elif relate_bsp1 is not None:
            # 如果已经有关联的买卖点，验证两个买卖点的klu是否一致
            assert self.relate_bsp1.klu.idx == relate_bsp1.klu.idx

    def add_feat(
        self,
        inp1: Union[str, Dict[str, float], Dict[str, Optional[float]], "CFeatures"],
        inp2: Optional[float] = None,
    ):
        """
        为买卖点添加特征。

        参数：
        inp1: 要添加的特征，可以是字符串、特征字典或CFeatures对象
        inp2: 需要设置的特征值（可选）
        """
        self.features.add_feat(inp1, inp2)

    def init_common_feature(self):
        """
        初始化通用特征，适用于所有买卖点。
        """
        # 将走势段或分段的振幅作为买卖点的通用特征
        self.add_feat(
            {
                "bsp_bi_amp": self.bi.amp(),
            }
        )
