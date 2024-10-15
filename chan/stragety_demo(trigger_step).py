import sys
import pandas as pd
from Chan import CChan
from ChanConfig import CChanConfig
from Common.CEnum import AUTYPE, BSP_TYPE, DATA_SRC, FX_TYPE, KL_TYPE
from Common.CTime import CTime
from DataAPI.csvAPI import CSV_API
from KLine.KLine_Unit import CKLine_Unit
from Plot.PlotMeta import CBS_Point_meta
import argparse
import json
import math
from datetime import datetime


class fx_t:
    def __init__(self):
        self.left = None
        self.middle = None
        self.right = None

    def reset(self, lv):
        self.left = lv[-3][-1]
        self.middle = lv[-2][-1]
        self.right = lv[-1][-1]

    def lowest(self):
        lo = min(self.left.low, self.middle.low, self.right.low)
        return lo


# 多头策略
class strategy_long_t:
    def __init__(self, delta_price=0.02, initial_capital=10000):
        self.delta_price = delta_price  # 卖出、买入时的价差
        self.holding = 0
        self.last_buy_price = 0
        self.lose_price = 0
        self.fx_bar = fx_t()  # 分形bar
        self.enable_stop_lose = True  # 是否止损，止损放在买入的最低价格
        # 统计数据
        self.total_return = 0
        self.win_num = 0
        self.win_return = 0
        self.lose_num = 0
        self.lose_return = 0
        self.buy_bar = None
        self.output_json_ = False
        # 新增：记录每笔交易的收益率和盈亏金额
        self.trade_returns = []
        self.trade_pnl = []  # 每笔交易的盈亏金额
        self.trade_durations = []  # 可选：记录每笔交易的持有时间
        # 新增：初始资金和当前资金
        self.initial_capital = initial_capital
        self.capital = initial_capital
        # 新增：最大回撤相关变量
        self.peak_capital = initial_capital
        self.max_drawdown = 0
        self.max_drawdown_start_time = None
        self.max_drawdown_end_time = None
        self.current_drawdown_start_time = None

    def output_json(self, v: bool):
        self.output_json_ = v

    def on_bar(self, cur_lv_chan, bar, bsp):
        global last_bsp  # 确保 last_bsp 是全局变量或适当传递
        bspm = CBS_Point_meta(last_bsp, last_bsp.is_segbsp)
        if self.holding != 0:
            self.__try_stop_lose(bar)
            self.__try_sell(cur_lv_chan, bar, bsp, bspm)
        else:
            self.__try_buy(cur_lv_chan, bar, bsp, bspm)

    # 纏論買入點
    def __try_buy(self, cur_lv_chan, bar, bsp, bspm):
        # try buy
        if not bsp.is_buy:
            return
        if (BSP_TYPE.T1P not in bsp.type) and (BSP_TYPE.T1 not in bsp.type):
            return
        if cur_lv_chan[-2].fx == FX_TYPE.BOTTOM:  # 底分型形成后开仓
            self.fx_bar.reset(cur_lv_chan)
            if bspm.desc() == "b1" or bspm.desc() == "b1p":
                self.buy_flag = False
                self.last_buy_price = (
                    bar.close + self.delta_price
                )  # 开仓价格为最后一根K线close
                self.holding = 1
                self.lose_price = self.fx_bar.lowest()
                self.buy_bar = bar
                lose_ratio = self.lose_price / self.last_buy_price - 1
                print(
                    f"{bar.time}: buy={self.last_buy_price:.3f}, lose={self.lose_price}({lose_ratio:.3f}), {bspm.desc()}"
                )
                if self.output_json_:
                    v = {
                        "time": bar.time.strftime("%Y-%m-%d %H:%M:%S"),
                        "action": "buy",
                        "price": self.last_buy_price,
                        "lose": self.lose_price,
                        "lose_ratio": self.lose_price / self.last_buy_price - 1,
                        "bspm": bspm.desc(),
                    }
                    print(json.dumps(v))
                return
            else:
                self.buy_flag = False
                print(f"{bar.time}: bsp not b1,b1p")

    def __do_sell(self, bar):
        sell_price = bar.close - self.delta_price
        profit_rate = sell_price / self.last_buy_price - 1 - 0.0005  # 考虑交易成本
        profit_amount = self.capital * profit_rate  # 计算实际盈亏金额
        self.capital += profit_amount  # 更新总资金
        self.total_return += profit_rate
        # 可选：计算持有时间
        delta = bar.time - self.buy_bar.time
        print(
            f"{bar.time}: sell price = {sell_price:.3f}, profit rate = {profit_rate * 100:.2f}%, profit amount = {profit_amount:.2f}, 持仓时间：{delta}"
        )
        if self.output_json_:
            v = {
                "time": bar.time.strftime("%Y-%m-%d %H:%M:%S"),
                "action": "sell",
                "price": sell_price,
                "ratio": profit_rate,
                "profit_amount": profit_amount,
                "持仓时间": delta,
            }
            print(json.dumps(v))
        self.holding = 0
        self.lose_price = 0
        self.buy_bar = None

        if profit_rate > 0:
            self.win_num += 1
            self.win_return += profit_rate
        else:
            self.lose_num += 1
            self.lose_return += profit_rate

        # 记录每笔交易的收益率和盈亏金额
        self.trade_returns.append(profit_rate)
        self.trade_pnl.append(profit_amount)
        # 可选：记录持有时间
        self.trade_durations.append(delta)

        # 更新最大回撤
        self.__update_drawdown(bar.time)

    # 止损
    def __try_stop_lose(self, bar):
        if self.holding == 0:
            return
        if self.enable_stop_lose:
            if self.lose_price > bar.close:  # 止损
                self.__do_sell(bar)

    # 纏論賣出點
    def __try_sell(self, cur_lv_list, bar, bsp, bspm):
        if self.holding == 0:
            return
        # try sell
        if bsp.is_buy:
            return
        # 当天有巨大涨幅
        if (BSP_TYPE.T2 not in bsp.type) and (BSP_TYPE.T2S not in bsp.type):
            return
        #
        if cur_lv_list[-2].fx == FX_TYPE.TOP:  # 顶分型形成后平仓
            self.__do_sell(bar)
            print(f"{bar.time}: sell")

    def __update_drawdown(self, current_time):
        # 更新峰值
        if self.capital > self.peak_capital:
            self.peak_capital = self.capital
            # 重置当前回撤开始时间
            self.current_drawdown_start_time = None
        else:
            # 计算当前回撤
            current_drawdown = self.peak_capital - self.capital
            if current_drawdown > self.max_drawdown:
                self.max_drawdown = current_drawdown
                self.max_drawdown_end_time = current_time
                # 如果当前回撤刚开始
                if self.current_drawdown_start_time is None:
                    self.current_drawdown_start_time = current_time
                self.max_drawdown_start_time = self.current_drawdown_start_time
            elif (
                self.capital < self.peak_capital
                and self.current_drawdown_start_time is None
            ):
                # 开始新的回撤
                self.current_drawdown_start_time = current_time

    def stop(self, bar):
        if self.holding != 0:
            # 还有持仓
            self.__do_sell(bar)
        if self.win_num == 0 and self.lose_num == 0:
            return
        print(f"初始资金: {self.initial_capital:.2f}")
        print(f"最终资金: {self.capital:.2f}")
        total_profit = self.capital - self.initial_capital
        print(
            f"总盈亏: {total_profit:.2f} ({(total_profit / self.initial_capital) * 100:.2f}%)"
        )
        print(
            f"total return: {(self.capital / self.initial_capital - 1) * 100:.2f}%, win={self.win_num}  lose={self.lose_num}"
        )
        print(
            f"win  return: {self.win_return * 100:.2f}%, avg win return={(self.win_return / self.win_num) * 100 if self.win_num != 0 else 0 :.2f}%"
        )
        print(
            f"lose return: {self.lose_return * 100:.2f}%, avg lose return={(self.lose_return / self.lose_num) * 100 if self.lose_num != 0 else 0 :.2f}%"
        )
        print(
            f"平均盈亏比: {abs((self.win_return / self.win_num) / (self.lose_return / self.lose_num)) if (self.lose_num != 0 and self.win_num != 0) else 0 :.2f} : 1"
        )
        print(f"胜率: {self.win_num / (self.win_num + self.lose_num):.4f}")

        # 计算盈利因子
        total_profit_trades = self.win_return
        total_loss_trades = abs(self.lose_return)
        profit_factor = (
            total_profit_trades / total_loss_trades
            if total_loss_trades != 0
            else math.inf
        )
        print(f"盈利因子: {profit_factor:.2f}")

        # 计算夏普比率
        # 假设无风险利率为0，夏普比率 = 平均收益率 / 标准差
        if len(self.trade_returns) > 1:
            avg_return = sum(self.trade_returns) / len(self.trade_returns)
            variance = sum((r - avg_return) ** 2 for r in self.trade_returns) / (
                len(self.trade_returns) - 1
            )
            std_dev = math.sqrt(variance)
            sharpe_ratio = avg_return / std_dev if std_dev != 0 else 0
        else:
            sharpe_ratio = 0
        print(f"夏普比率: {sharpe_ratio:.2f}")

        # 计算Sortino比率
        # Sortino比率 = (平均收益率 - 目标收益率) / 下行标准差
        target_return = 0  # 通常设为0
        downside_returns = [
            r - target_return for r in self.trade_returns if r < target_return
        ]
        if downside_returns:
            downside_variance = sum(
                (r - target_return) ** 2 for r in downside_returns
            ) / (len(downside_returns) - 1)
            downside_std_dev = math.sqrt(downside_variance)
            sortino_ratio = (
                (avg_return - target_return) / downside_std_dev
                if downside_std_dev != 0
                else 0
            )
        else:
            sortino_ratio = math.inf
        print(f"Sortino比率: {sortino_ratio:.2f}")

        # 计算总盈亏金额
        total_pnl = sum(self.trade_pnl)
        print(f"总盈亏金额: {total_pnl:.2f}")

        # 计算最大回撤
        print(
            f"最大回撤: {self.max_drawdown:.2f} ({(self.max_drawdown / self.initial_capital) * 100:.2f}%)"
        )

        # 进一步详细输出回撤时间
        if self.max_drawdown_start_time and self.max_drawdown_end_time:
            duration = self.max_drawdown_end_time - self.max_drawdown_start_time
            print(f"最大回撤持续时间: {duration}")
            print(
                f"最大回撤发生时间段: {self.max_drawdown_start_time} 至 {self.max_drawdown_end_time}"
            )

        if self.output_json_:
            v = {
                "report": 1,
                "initial_capital": self.initial_capital,
                "final_capital": self.capital,
                "total_pnl": total_pnl,
                "total_return": (self.capital / self.initial_capital - 1),
                "win-num": self.win_num,
                "lose-num": self.lose_num,
                "win-return": self.win_return,
                "lose-return": self.lose_return,
                "profit-factor": profit_factor,
                "sharpe-ratio": sharpe_ratio,
                "sortino-ratio": sortino_ratio,
                "max_drawdown": self.max_drawdown,
                "max_drawdown_percentage": (self.max_drawdown / self.initial_capital),
                "max_drawdown_start_time": (
                    self.max_drawdown_start_time.strftime("%Y-%m-%d %H:%M:%S")
                    if self.max_drawdown_start_time
                    else None
                ),
                "max_drawdown_end_time": (
                    self.max_drawdown_end_time.strftime("%Y-%m-%d %H:%M:%S")
                    if self.max_drawdown_end_time
                    else None
                ),
                "total_pnl": total_pnl,
            }
            print(json.dumps(v))


def create_cchan_object(code, lv_list, begin_time, end_time, data_src):
    config = CChanConfig(
        {
            "bi_strict": True,
            "bi_fx_check": "strict",  # strict：底分型的最低点必须比顶分型 3 元素最低点的最小值还低，顶分型反之。
            "trigger_step": True,
            "skip_step": 0,
            "divergence_rate": float("inf"),
            "bsp2_follow_1": True,
            "bsp3_follow_1": True,
            "min_zs_cnt": 1,
            "bs1_peak": False,
            "macd_algo": "peak",
            "bs_type": "1,2,3a,1p,2s,3b",
            "print_warning": True,
            "zs_combine": True,
            "zs_combine_mode": "peak",  # zs_combine_mode设置成peak，默认是zs的区间有重叠才合并。
        }
    )

    # code = code[:2] + "." + code[2:]
    chan = CChan(
        code=code,
        begin_time=begin_time,
        end_time=end_time,
        data_src=data_src,
        lv_list=lv_list,
        config=config,
        autype=AUTYPE.QFQ,
    )

    return chan


if __name__ == "__main__":
    """
    一个极其弱智的策略，只交易一类买卖点，底分型形成后就开仓，直到一类卖点顶分型形成后平仓
    只用做展示如何自己实现策略，做回测用~
    """

    code = "BTCUSDT"  # 设置交易品种，如BTCUSDT（比特币/美元）
    begin_time = "2024-09-01"
    # end_time = "2024-10-07"
    end_time = None
    data_src_type = DATA_SRC.CSV  # 使用CSV数据源
    k_type = KL_TYPE.K_5M
    lv_list = [k_type]  # 级别列表
    # 初始化数据源（CSV）
    data_src = CSV_API(
        code,
        k_type=k_type,
        begin_time=begin_time,
        end_time=end_time,
        autype=AUTYPE.QFQ,  # 前复权
        # file_path="./Data",  # 新增参数：保存CSV的目录路径
    )  # 初始化数据源实例
    data = data_src.get_kl_data()
    chan = create_cchan_object(code, lv_list, begin_time, end_time, data_src)
    strategy = strategy_long_t(delta_price=0.00, initial_capital=10000)

    # 遍历 DataFrame 的每一行
    last_bar = None
    for coint, klu in enumerate(data, start=1):
        # print(f"当前计数：{coint}，当前k线：{klu}")
        d1 = {lv_list[0]: [klu]}
        chan.trigger_load(d1)
        #
        bsp_list = chan.get_bsp()  # 获取买卖点列表
        if not bsp_list:  # 为空
            continue
        last_bsp = bsp_list[-1]  # 最后一个买卖点
        bspm = CBS_Point_meta(last_bsp, last_bsp.is_segbsp)
        cur_lv_chan = chan[0]
        last_bar = cur_lv_chan[-1][-1]
        strategy.on_bar(cur_lv_chan, last_bar, last_bsp)

    # 执行策略结束后的统计
    strategy.stop(last_bar)
