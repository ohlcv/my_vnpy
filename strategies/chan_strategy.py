# chan_strategy.py

from vnpy_ctastrategy import (
    CtaTemplate,
    StopOrder,
    TickData,
    BarData,
    TradeData,
    OrderData,
)


from vnpy_ctastrategy.chan.Chan import CChan  # 更新导入路径
from vnpy_ctastrategy.chan.ChanConfig import CChanConfig
from vnpy_ctastrategy.chan.KLine.KLine_Unit import CKLine_Unit
from vnpy_ctastrategy.chan.Common.CTime import CTime
from vnpy_ctastrategy.chan.DataAPI.vnpyAPI import C_VnpyDataApi
from vnpy_ctastrategy.chan.Common.CEnum import (
    AUTYPE,
    BSP_TYPE,
    FX_TYPE,
    KL_TYPE,
    DATA_FIELD,
)


class ChanStrategy(CtaTemplate):
    """
    基于缠论的策略，继承自 CtaTemplate。
    该策略只交易一种买卖点类型，底分型形成后开仓，顶分型形成后平仓。
    """

    author = "用Python的交易员"

    # 策略参数
    entry_window = 20
    exit_window = 10
    atr_window = 20
    fixed_size = 1

    # 策略变量
    entry_up = 0
    entry_down = 0
    exit_up = 0
    exit_down = 0
    atr_value = 0

    long_entry = 0
    short_entry = 0
    long_stop = 0
    short_stop = 0

    parameters = ["entry_window", "exit_window", "atr_window", "fixed_size"]
    variables = ["entry_up", "entry_down", "exit_up", "exit_down", "atr_value"]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        # 初始化 CChan 对象
        config = CChanConfig(
            {
                "trigger_step": True,
                "divergence_rate": 0.8,
                "min_zs_cnt": 1,
                "max_kl_inconsistent_cnt": 100,  # 示例配置
                "max_kl_misalgin_cnt": 100,  # 示例配置
                "auto_skip_illegal_sub_lv": True,  # 示例配置
                "print_warning": True,  # 示例配置
                "print_err_time": True,  # 示例配置
            }
        )
        self.k_type = KL_TYPE.K_1M
        self.chan = CChan(
            code=vt_symbol,  # 股票代码或交易对符号
            begin_time=None,
            end_time=None,
            data_src="custom:vnpyAPI.C_VnpyDataApi",  # 使用自定义数据源
            lv_list=[self.k_type],
            config=config,
            autype=AUTYPE.QFQ,  # 复权类型
        )

        # 初始化数据源
        C_VnpyDataApi.do_init()

        # 持仓状态和买入价格
        self.is_hold = False
        self.last_buy_price = None

    def on_init(self):
        """策略初始化"""
        self.write_log("策略初始化")
        # 加载历史数据
        for klu in self.chan.load():
            self.write_log(f"加载K线: {klu}")
        self.write_log("策略初始化完成")

    def on_start(self):
        """策略启动"""
        self.write_log("策略启动")

    def on_stop(self):
        """策略停止"""
        self.write_log("策略停止")

    def on_tick(self, tick: TickData):
        """收到新Tick数据时的回调"""
        pass  # 本策略不使用 Tick 数据

    def on_bar(self, bar: BarData):
        """收到新的K线数据时的回调"""
        # 将新的K线数据喂给CChan进行处理
        klu = self.convert_bar_to_klu(bar)
        self.chan.trigger_load({self.k_type: [klu]})
        self.write_log(f"喂入新K线: {klu}")

        # 获取买卖点列表
        bsp_list = self.chan.get_bsp()
        if not bsp_list:
            return

        # 获取最新的买卖点
        last_bsp = bsp_list[-1]

        # 仅处理T1和T1P类型的买卖点
        if BSP_TYPE.T1 not in last_bsp.type and BSP_TYPE.T1P not in last_bsp.type:
            return

        # 获取当前级别的K线数据
        cur_lv_chan = self.chan[0]

        # 检查最新买卖点的K线索引是否与当前级别的倒数第二根K线索引一致
        if last_bsp.klu.klc.idx != cur_lv_chan[-2].idx:
            return

        # 判断是否为买入信号
        if (
            cur_lv_chan[-2].fx == FX_TYPE.BOTTOM
            and last_bsp.is_buy
            and not self.is_hold
        ):
            self.last_buy_price = cur_lv_chan[-1][-1].close
            self.buy(bar.close_price, self.fixed_size)
            self.write_log(f"买入信号触发，价格: {self.last_buy_price}")
            self.is_hold = True

        # 判断是否为卖出信号
        elif cur_lv_chan[-2].fx == FX_TYPE.TOP and not last_bsp.is_buy and self.is_hold:
            sell_price = cur_lv_chan[-1][-1].close
            profit_rate = (sell_price - self.last_buy_price) / self.last_buy_price * 100
            self.sell(sell_price, self.fixed_size)
            self.write_log(
                f"卖出信号触发，价格: {sell_price}, 盈利率: {profit_rate:.2f}%"
            )
            self.is_hold = False

    def on_trade(self, trade: TradeData):
        """收到成交数据时的回调"""
        self.write_log(
            f"成交: {trade.direction}, 价格: {trade.price}, 数量: {trade.volume}"
        )

    def on_order(self, order: OrderData):
        """收到订单数据时的回调"""
        pass  # 本策略不处理订单状态更新

    def on_stop_order(self, stop_order: StopOrder):
        """收到条件单数据时的回调"""
        pass  # 本策略不处理条件单

    def convert_bar_to_klu(self, bar: BarData) -> CKLine_Unit:
        """
        将 vn.py 的 BarData 转换为 CChan 的 CKLine_Unit 对象。
        """
        kl_dict = {
            DATA_FIELD.FIELD_TIMESTAMP: bar.datetime.timestamp(),
            DATA_FIELD.FIELD_TIME: bar.datetime,
            DATA_FIELD.FIELD_OPEN: float(bar.open_price),
            DATA_FIELD.FIELD_CLOSE: float(bar.close_price),
            DATA_FIELD.FIELD_HIGH: float(bar.high_price),
            DATA_FIELD.FIELD_LOW: float(bar.low_price),
            DATA_FIELD.FIELD_VOLUME: float(bar.volume),
        }
        return CKLine_Unit(kl_dict)

    def on_close(self):
        """策略关闭时的清理工作"""
        C_VnpyDataApi.do_close()
