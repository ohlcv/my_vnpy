# chan_strategy.py

from vnpy_ctastrategy import (
    CtaTemplate,
    StopOrder,
    Direction,
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
    fixed_size = 1

    # 策略变量
    inLong = False
    inShort = False
    long_entry_price = 0
    short_entry_price = 0
    long_stoploss_price = 0
    short_stoploss_price = 0

    last_b1_price = 0
    last_s1_price = 0

    parameters = ["fixed_size"]
    variables = ["last_b1_price", "last_s1_price"]

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

    def on_init(self):
        """策略初始化"""
        self.write_log("策略初始化")
        self.load_bar(20)  # 加载20根K线
        # 加载历史数据
        # for klu in self.chan.load():
        #     self.write_log(f"加载K线: {klu}")

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
        self.cancel_all()  # 取消所有未成交的订单

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
        last_bsp_type = last_bsp.type[0]
        last_bsp_volume = last_bsp.klu.trade_info.metric.get('volume')
        cur_lv_chan = self.chan[0]  # 获取第一个级别的CKLine_List
        last_fx_type = cur_lv_chan[-2].fx
        last_klc = cur_lv_chan[-1]
        last_klu_volume = last_klc[-1].trade_info.metric.get('volume')

        if last_bsp_type == BSP_TYPE.T1 or BSP_TYPE.T1P and last_bsp.is_buy: 
            if cur_lv_chan[-2].fx == FX_TYPE.BOTTOM:
                self.last_b1_price = last_bsp.klu.low
            elif cur_lv_chan[-2].fx == FX_TYPE.TOP:
                self.last_s1_price = last_bsp.klu.high
        
        # 仅处理T2和T2S类型的买卖点
        if BSP_TYPE.T2 not in last_bsp.type and BSP_TYPE.T2S not in last_bsp.type:
            return

        # 检查最新买卖点的K线索引是否与当前级别的倒数第二根K线索引一致
        if last_bsp.klu.klc.idx != cur_lv_chan[-2].idx:
            return

        if not self.pos:
            # 重置多空入场和止损价格
            self.long_entry_price = 0
            self.short_entry_price = 0
            self.long_stoploss_price = 0
            self.short_stoploss_price = 0

        # 判断是否为买入信号
        buy_signal = (
            last_bsp.is_buy
            and cur_lv_chan[-2].fx == FX_TYPE.BOTTOM
            and (last_bsp_type == BSP_TYPE.T2 or last_bsp_type == BSP_TYPE.T2S)
        )

        # 判断是否为卖出信号
        sell_signal = (
            not last_bsp.is_buy
            and cur_lv_chan[-2].fx == FX_TYPE.TOP
            and (last_bsp_type == BSP_TYPE.T2 or last_bsp_type == BSP_TYPE.T2S)
        )

        if buy_signal:
            if self.pos < 0:
                self.cover(bar.close_price, abs(self.pos))  # 平空
            if self.pos == 0:
                self.buy(bar.close_price, self.fixed_size)
        if sell_signal:
            if self.pos > 0:
                self.sell(bar.close_price, abs(self.pos))   # 平多
            if self.pos == 0:
                self.short(bar.close_price, self.fixed_size)    # 做空


    def on_trade(self, trade: TradeData):
        """收到成交数据时的回调"""
        self.write_log(
            f"成交: {trade.direction}, 价格: {trade.price}, 数量: {trade.volume}"
        )
        if trade.direction == Direction.LONG:  # 如果是多头成交
            self.long_entry_price = trade.price  # 记录多头入场价
            self.long_stoploss_price = self.last_b1_price  # 设置多头止损
            self.write_log(f"多头入场，价格: {self.long_entry_price}, 止损价: {self.long_stoploss_price}")
        elif trade.direction == Direction.SHORT:  # 如果是空头成交
            self.short_entry_price = trade.price  # 记录空头入场价
            self.short_stoploss_price = self.last_s1_price  # 设置空头止损
            self.write_log(f"空头入场，价格: {self.short_entry_price}, 止损价: {self.short_stoploss_price}")

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
