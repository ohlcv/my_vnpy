import os
import csv
from datetime import datetime
import ccxt
import pytz  # 引入pytz库进行时区处理

from Common.CEnum import AUTYPE, DATA_FIELD, KL_TYPE
from Common.CTime import CTime
from Common.func_util import kltype_lt_day, str2float
from KLine.KLine_Unit import CKLine_Unit

from .CommonStockAPI import CCommonStockApi


def GetColumnNameFromFieldList(fields: str):
    """
    根据传入的字段名称字符串，返回字段枚举列表。

    :param fields: 用逗号分隔的字段名称字符串。
    :return: 字段枚举的列表。
    """
    _dict = {
        "datetime": DATA_FIELD.FIELD_DATETIME,
        "time": DATA_FIELD.FIELD_TIME,
        "timestamp": DATA_FIELD.FIELD_TIMESTAMP,  # 添加时间戳字段
        "open": DATA_FIELD.FIELD_OPEN,
        "high": DATA_FIELD.FIELD_HIGH,
        "low": DATA_FIELD.FIELD_LOW,
        "close": DATA_FIELD.FIELD_CLOSE,
        "volume": DATA_FIELD.FIELD_VOLUME,
    }
    return [_dict[x] for x in fields.split(",")]


class CCXT(CCommonStockApi):
    is_connect = None  # 类变量，用于表示是否已连接

    def __init__(
        self,
        code,
        k_type=KL_TYPE.K_DAY,
        begin_time=None,
        end_time=None,
        autype=AUTYPE.QFQ,
        save_csv=False,  # 新增参数：是否保存数据到CSV
        csv_path=None,  # 新增参数：保存CSV的目录路径
    ):
        """
        初始化CCXT类实例。

        :param code: 股票代码或交易对符号。
        :param k_type: K线类型，默认为日K线。
        :param begin_time: 开始日期。
        :param end_time: 结束日期。
        :param autype: 复权类型。
        :param save_csv: 是否保存数据到CSV文件。
        :param csv_path: 保存CSV文件的目录路径。
        """
        super(CCXT, self).__init__(code, k_type, begin_time, end_time, autype)
        self.save_csv = save_csv
        # 确保 begin_time 包含时间
        if begin_time:
            # 如果传入的日期只有日期部分，则加上时间部分
            if len(begin_time) == 10:  # YYYY-MM-DD格式
                self.begin_time = f"{begin_time} 00:00:00"
            else:
                self.begin_time = begin_time
        else:
            self.begin_time = None
        # 如果 csv_path 没有传入，则自动生成默认路径
        if csv_path is None:
            try:
                # 获取当前文件目录
                current_file_dir = os.path.dirname(os.path.realpath(__file__))
                # print(f"Current file directory: {current_file_dir}")

                # 获取当前文件目录的父目录
                base_dir = os.path.dirname(current_file_dir)
                # print(f"Parent directory: {base_dir}")

                # 获取父目录的父目录
                parent_dir = os.path.dirname(base_dir)
                # print(f"Base directory (two levels up): {parent_dir}")

                # 在父目录的父目录中创建 Data 文件夹，并加入 code 和 k_type.name
                self.csv_path = os.path.join(
                    parent_dir, "Data", self.code, self.k_type.name
                )
                # print(f"CSV path set to: {self.csv_path}")
            except Exception as e:
                print(f"Error setting csv_path: {e}")
                raise
        else:
            self.csv_path = csv_path
            # print(f"CSV path provided: {self.csv_path}")

    def get_kl_data(self):
        """
        获取K线数据，限制每次最多获取100条K线，循环获取所有所需数据，并在获取过程中打印进度。
        如果设置了保存CSV参数，则在获取完成后保存数据到CSV文件。
        """
        fields = "time,open,high,low,close,volume"  # 需要获取的字段
        exchange = ccxt.binance()  # 实例化ccxt的Binance交易所对象
        timeframe = self.__convert_type()  # 转换K线类型为ccxt库所需格式

        # 将begin_time转换为毫秒时间戳格式，ccxt使用UTC时间
        since_date = (
            exchange.parse8601(f"{self.begin_time}T00:00:00Z")
            if self.begin_time
            else None
        )

        all_data = []  # 用于存储所有获取的K线数据
        total_fetched = 0  # 总共获取的K线数量
        batch_number = 0  # 批次编号

        # 定义时区
        utc = pytz.UTC
        shanghai = pytz.timezone("Asia/Shanghai")

        while True:
            limit = 100  # 每次请求最多获取100条K线数据
            try:
                # 获取OHLCV数据，包含时间戳、开盘价、最高价、最低价、收盘价和成交量
                data = exchange.fetch_ohlcv(
                    self.code, timeframe, since=since_date, limit=limit
                )
            except Exception as e:
                print(f"Error fetching data: {e}")
                break  # 出现错误时退出循环

            if not data:
                print("没有更多数据可获取。")
                break  # 如果没有更多数据，退出循环

            batch_number += 1  # 增加批次数量
            print(f"开始处理第 {batch_number} 批数据，共 {len(data)} 条K线。")

            for item in data:
                # 将时间戳转换为datetime对象，设置为UTC时区
                time_obj = datetime.fromtimestamp(item[0] / 1000, tz=utc)
                # 转换为上海时区
                time_obj = time_obj.astimezone(shanghai)
                time_str = time_obj.strftime("%Y-%m-%d %H:%M:%S")
                timestamp = str(item[0])
                # 构建K线数据条目，包括时间、时间戳、开、高、低、收、量
                item_data = [
                    time_str,
                    item[1],
                    item[2],
                    item[3],
                    item[4],
                    item[5],
                ]

                # 创建字典并打印以检查内容
                item_dict = self.create_item_dict(
                    item_data, GetColumnNameFromFieldList(fields)
                )
                # print(f"生成的字典: {item_dict}")  # 打印生成的字典

                # 创建CKLine_Unit对象并添加到all_data列表
                kl_unit = CKLine_Unit(
                    item_dict, autofix=True
                )  # 这里假设 item_dict 是个正确的字典
                all_data.append(kl_unit)
                yield kl_unit  # 生成K线数据项

            total_fetched += len(data)  # 更新总获取数量
            print(f"已获取 {total_fetched} 条K线数据。")

            # 更新since_date为最后一条数据的时间戳加上一个时间单位，防止重复
            last_timestamp = data[-1][0]
            since_date = last_timestamp + 1  # 增加1毫秒

            # 如果end_time已设置，并且最后一条数据的时间超过end_time，则停止获取
            if self.end_time:
                last_date = datetime.fromtimestamp(
                    last_timestamp / 1000, tz=utc
                ).astimezone(shanghai)
                if last_date.strftime("%Y-%m-%d") >= self.end_time:
                    print("已达到结束日期，停止数据获取。")
                    break

        # 获取完成后，如果设置了保存CSV，则调用保存函数
        if self.save_csv:
            self.save_to_csv(all_data)

    def save_to_csv(self, data):
        """
        将获取的K线数据保存到CSV文件，保存必要的字段，并增加一列时间戳。

        :param data: CKLine_Unit对象的列表。
        """
        if not data:
            print("没有数据可保存到CSV。")
            return

        # 生成文件名
        filename = f"{self.code.replace('/', '_')}_{self.k_type.name}.csv"
        full_path = os.path.join(self.csv_path, filename)

        # 确保保存CSV的目录存在
        try:
            os.makedirs(self.csv_path, exist_ok=True)
        except PermissionError as pe:
            print(f"创建目录失败，权限被拒绝: {pe}")
            raise
        except Exception as e:
            print(f"创建目录失败: {e}")
            raise

        # 定义需要保存的字段，并增加时间戳字段
        fields = "datetime,open,high,low,close,volume"
        headers = GetColumnNameFromFieldList(fields)

        try:
            with open(full_path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=headers)
                writer.writeheader()
                for kl_unit in data:
                    # 提取需要的字段
                    row = {
                        # DATA_FIELD.FIELD_TIME: kl_unit.time.to_str(),  # 已包含时间信息
                        # DATA_FIELD.FIELD_TIMESTAMP: kl_unit.timestamp,  # 提取时间戳
                        DATA_FIELD.FIELD_DATETIME: kl_unit.time.to_datetime(),
                        DATA_FIELD.FIELD_OPEN: kl_unit.open,
                        DATA_FIELD.FIELD_HIGH: kl_unit.high,
                        DATA_FIELD.FIELD_LOW: kl_unit.low,
                        DATA_FIELD.FIELD_CLOSE: kl_unit.close,
                        DATA_FIELD.FIELD_VOLUME: kl_unit.trade_info.metric.get(
                            "volume", None
                        ),  # 通过 metric 获取 volume
                    }
                    writer.writerow(row)
            print(f"数据已保存到 {full_path}")
        except PermissionError as pe:
            print(f"写入文件失败，权限被拒绝: {pe}")
            raise
        except Exception as e:
            print(f"保存CSV时出错: {e}")
            raise

    # 其余方法保持不变
    def SetBasciInfo(self):
        """
        设置基本信息，未实现具体功能。
        """
        pass

    @classmethod
    def do_init(cls):
        """
        类方法，初始化操作，未实现具体功能。
        """
        pass

    @classmethod
    def do_close(cls):
        """
        类方法，关闭操作，未实现具体功能。
        """
        pass

    def __convert_type(self):
        """
        将K线类型转换为ccxt所需的时间周期格式。

        :return: ccxt所需的时间周期字符串。
        """
        _dict = {
            KL_TYPE.K_DAY: "1d",
            KL_TYPE.K_WEEK: "1w",
            KL_TYPE.K_MON: "1M",
            KL_TYPE.K_1M: "1m",
            KL_TYPE.K_5M: "5m",
            KL_TYPE.K_15M: "15m",
            KL_TYPE.K_30M: "30m",
            KL_TYPE.K_60M: "1h",
        }
        return _dict[self.k_type]

    # 工具函数：解析时间字符串为 CTime 对象
    def parse_time_column(self, inp):
        """
        将时间字符串解析为 CTime 对象。根据时间格式的不同，做出不同的解析。
        支持以下格式：
        - 10位格式：YYYY-MM-DD
        - 17位格式：YYYYMMDDHHMM00000
        - 19位格式：YYYY-MM-DD HH:MM:SS
        - 新增格式：YYYY/MM/DD HH:MM

        :param inp: str，时间字符串
        :return: CTime 对象，表示解析后的时间
        """
        # 根据时间字符串的长度和格式，解析不同格式的时间
        if len(inp) == 10:  # 格式 YYYY-MM-DD
            year = int(inp[:4])
            month = int(inp[5:7])
            day = int(inp[8:10])
            hour = minute = 0  # 没有时间信息，默认为 0
        elif len(inp) == 17:  # 格式 YYYYMMDDHHMM00000
            year = int(inp[:4])
            month = int(inp[4:6])
            day = int(inp[6:8])
            hour = int(inp[8:10])
            minute = int(inp[10:12])
            second = int(inp[12:14])
        elif len(inp) == 19 and " " in inp:  # 格式 YYYY-MM-DD HH:MM:SS
            year = int(inp[:4])
            month = int(inp[5:7])
            day = int(inp[8:10])
            hour = int(inp[11:13])
            minute = int(inp[14:16])
            second = int(inp[17:19])
        elif len(inp) == 16 and "/" in inp:  # 新增格式 YYYY/MM/DD HH:MM
            year = int(inp[:4])
            month = int(inp[5:7])
            day = int(inp[8:10])
            hour = int(inp[11:13])
            minute = int(inp[14:16])
        else:
            # 如果时间格式不符合预期，抛出异常
            raise Exception(f"unknown time column from csv:{inp}")
        # 返回解析后的 CTime 对象
        return CTime(year, month, day, hour, minute, second)

    def create_item_dict(self, data, column_name):
        """
        根据数据和列名创建字典，将每列数据与相应的列名一一对应，并进行必要的数据类型转换。

        处理逻辑：
        - 如果列为时间字段（第一个字段），调用 `parse_time_column` 方法解析时间字符串为 `CTime` 对象。
        - 其他列则将字符串数据转换为浮点数类型，便于后续数据处理。

        :param data: List[str] - 数据列表，每个元素代表一列的数据（如["2024-10-09 00:00", "100.5", "101.0", ...]）。
        :param column_name: List[str] - 列名列表，对应 `data` 中每列的名称（如 ["时间", "开盘价", "最高价", ...]）。
        :return: dict - 返回一个字典，其中键为列名，值为对应的数据值（如 {"时间": CTime对象, "开盘价": 100.5, ...}）。
        """
        for i in range(len(data)):
            # 如果是第一列数据（时间字段），调用 parse_time_column 方法进行解析
            if i == 0:
                data[i] = self.parse_time_column(data[i])  # 转换为 CTime 对象
            else:
                # 否则，调用 str2float 将字符串数据转换为浮点数
                data[i] = str2float(data[i])

        # 将列名（column_name）与数据（data）组合成字典，并返回
        return dict(zip(column_name, data))
