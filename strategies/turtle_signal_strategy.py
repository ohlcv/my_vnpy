from vnpy_ctastrategy import (
    CtaTemplate,
    StopOrder,
    Direction,
    TickData,
    BarData,
    TradeData,
    OrderData,
    BarGenerator,
    ArrayManager,
)


class TurtleSignalStrategy(CtaTemplate):
    """
    海龟交易策略类，继承自CtaTemplate。
    基于唐奇安通道的突破策略，结合ATR进行仓位管理。
    """

    author = "用Python的交易员"

    # 策略参数
    entry_window = 20  # 入场通道窗口大小
    exit_window = 10  # 出场通道窗口大小
    atr_window = 20  # ATR窗口大小
    fixed_size = 1  # 固定下单手数

    # 策略变量
    entry_up = 0  # 入场通道上轨
    entry_down = 0  # 入场通道下轨
    exit_up = 0  # 出场通道上轨
    exit_down = 0  # 出场通道下轨
    atr_value = 0  # ATR值

    long_entry = 0  # 多头入场价格
    short_entry = 0  # 空头入场价格
    long_stop = 0  # 多头止损价格
    short_stop = 0  # 空头止损价格

    # 参数和变量声明，用于在界面中显示
    parameters = ["entry_window", "exit_window", "atr_window", "fixed_size"]
    variables = ["entry_up", "entry_down", "exit_up", "exit_down", "atr_value"]

    def __init__(self, cta_engine, strategy_name, vt_symbol, setting):
        """
        初始化策略实例，传入cta_engine、策略名称、交易标的和配置参数。
        """
        super().__init__(cta_engine, strategy_name, vt_symbol, setting)

        # 使用BarGenerator生成K线
        self.bg = BarGenerator(self.on_bar)
        # 使用ArrayManager管理K线数据
        self.am = ArrayManager()

    def on_init(self):
        """
        策略初始化回调，加载历史数据并初始化策略。
        """
        self.write_log("策略初始化")
        self.load_bar(20)  # 加载20根K线

    def on_start(self):
        """
        策略启动回调，策略启动时调用。
        """
        self.write_log("策略启动")

    def on_stop(self):
        """
        策略停止回调，策略停止时调用。
        """
        self.write_log("策略停止")

    def on_tick(self, tick: TickData):
        """
        Tick数据更新回调，处理新的Tick数据。
        """
        self.bg.update_tick(tick)  # 更新Tick数据到BarGenerator中

    def on_bar(self, bar: BarData):
        """
        K线数据更新回调，处理新的K线数据。
        """
        # 打印当前K线的所有信息
        # self.write_log(f"新K线数据: {self.format_bar(bar)}")
        # print(f"新K线数据: {self.format_bar(bar)}")

        self.cancel_all()  # 取消所有未成交的订单

        self.am.update_bar(bar)  # 更新ArrayManager的K线数据
        if not self.am.inited:  # 如果数据尚未初始化，则不执行策略
            return

        # 当没有持仓时，计算入场通道
        if not self.pos:
            self.entry_up, self.entry_down = self.am.donchian(
                self.entry_window
            )  # 计算唐奇安通道

        # 每根K线都计算出场通道
        self.exit_up, self.exit_down = self.am.donchian(self.exit_window)

        if not self.pos:
            # 计算ATR值，用于止损设置
            self.atr_value = self.am.atr(self.atr_window)

            # 重置多空入场和止损价格
            self.long_entry = 0
            self.short_entry = 0
            self.long_stop = 0
            self.short_stop = 0

            # 发出买入和做空订单
            self.send_buy_orders(self.entry_up)
            self.send_short_orders(self.entry_down)

        elif self.pos > 0:  # 如果持有多头仓位
            self.send_buy_orders(self.entry_up)  # 继续加仓

            sell_price = max(self.long_stop, self.exit_down)  # 计算卖出价
            self.sell(sell_price, abs(self.pos), True)  # 卖出平仓

        elif self.pos < 0:  # 如果持有空头仓位
            self.send_short_orders(self.entry_down)  # 继续加仓

            cover_price = min(self.short_stop, self.exit_up)  # 计算回补价
            self.cover(cover_price, abs(self.pos), True)  # 回补空头

        self.put_event()  # 更新策略状态

    def on_trade(self, trade: TradeData):
        """
        成交数据更新回调，处理新的成交数据。
        """
        if trade.direction == Direction.LONG:  # 如果是多头成交
            self.long_entry = trade.price  # 记录多头入场价
            self.long_stop = self.long_entry - 2 * self.atr_value  # 设置多头止损
        else:  # 如果是空头成交
            self.short_entry = trade.price  # 记录空头入场价
            self.short_stop = self.short_entry + 2 * self.atr_value  # 设置空头止损

    def on_order(self, order: OrderData):
        """
        订单更新回调，处理订单状态更新。
        """
        pass  # 此处不处理订单事件

    def on_stop_order(self, stop_order: StopOrder):
        """
        条件单更新回调，处理条件单状态更新。
        """
        pass  # 此处不处理条件单事件

    def send_buy_orders(self, price):
        """
        根据价格分批发送买入订单，逐步加仓。
        """
        t = self.pos / self.fixed_size  # 计算当前仓位

        if t < 1:
            self.buy(price, self.fixed_size, True)  # 第一笔买入

        if t < 2:
            self.buy(price + self.atr_value * 0.5, self.fixed_size, True)  # 第二笔买入

        if t < 3:
            self.buy(price + self.atr_value, self.fixed_size, True)  # 第三笔买入

        if t < 4:
            self.buy(price + self.atr_value * 1.5, self.fixed_size, True)  # 第四笔买入

    def send_short_orders(self, price):
        """
        根据价格分批发送做空订单，逐步加仓。
        """
        t = self.pos / self.fixed_size  # 计算当前仓位

        if t > -1:
            self.short(price, self.fixed_size, True)  # 第一笔做空

        if t > -2:
            self.short(
                price - self.atr_value * 0.5, self.fixed_size, True
            )  # 第二笔做空

        if t > -3:
            self.short(price - self.atr_value, self.fixed_size, True)  # 第三笔做空

        if t > -4:
            self.short(
                price - self.atr_value * 1.5, self.fixed_size, True
            )  # 第四笔做空

    def format_bar(self, bar: BarData) -> str:
        """
        格式化K线数据为字符串，便于打印。

        参数:
            bar (BarData): 当前的K线数据

        返回:
            str: 格式化后的K线信息字符串
        """
        return (
            f"Symbol: {bar.symbol}, "
            f"Exchange: {bar.exchange.value}, "
            f"Datetime: {bar.datetime}, "
            f"Interval: {bar.interval.value if bar.interval else 'None'}, "
            f"Volume: {bar.volume}, "
            f"Turnover: {bar.turnover}, "
            f"Open Interest: {bar.open_interest}, "
            f"Open Price: {bar.open_price}, "
            f"High Price: {bar.high_price}, "
            f"Low Price: {bar.low_price}, "
            f"Close Price: {bar.close_price}"
        )
