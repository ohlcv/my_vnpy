import os
import csv
from datetime import datetime


from ..Common.CEnum import AUTYPE, DATA_FIELD, KL_TYPE  # 数据字段和K线类型枚举
from ..Common.ChanException import CChanException, ErrCode  # 自定义异常类和错误码
from ..Common.CTime import CTime  # 时间处理类
from ..Common.func_util import kltype_lt_day, str2float  # 字符串转浮点数的工具函数
from ..KLine.KLine_Unit import CKLine_Unit  # 自定义的K线数据单元类

from .CommonStockAPI import CCommonStockApi  # 从当前目录导入基类 CCommonStockApi


# 工具函数：将CSV中的一行数据解析为字典格式
def create_item_dict(data, column_name):
    """
    将一行CSV数据转换为字典，键为列名，值为对应的数据。
    - 如果列名是时间列，则进行时间解析。
    - 否则，将字符串数据转为浮点数。

    :param data: list，每行数据值的列表
    :param column_name: list，对应列名的列表
    :return: dict，将数据转换为以列名为键的数据字典
    """
    for i in range(len(data)):
        # 根据列名判断是否为时间列，如果是则解析为 CTime 对象，否则将字符串转换为浮点数
        data[i] = (
            parse_time_column(data[i])
            if column_name[i] == DATA_FIELD.FIELD_TIME
            else str2float(data[i])
        )
    # 使用 zip 将列名和数据值组合成字典
    return dict(zip(column_name, data))


# 工具函数：解析时间字符串为 CTime 对象
def parse_time_column(inp):
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
    elif len(inp) == 19 and " " in inp:  # 格式 YYYY-MM-DD HH:MM:SS
        year = int(inp[:4])
        month = int(inp[5:7])
        day = int(inp[8:10])
        hour = int(inp[11:13])
        minute = int(inp[14:16])
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
    return CTime(year, month, day, hour, minute)


# CSV数据处理API类，继承自 CCommonStockApi
class CSV_API(CCommonStockApi):
    def __init__(
        self,
        code,
        k_type=KL_TYPE.K_DAY,
        begin_time=None,
        end_time=None,
        autype=None,
        file_path=None,
    ):
        """
        CSV_API 的初始化方法，用于设定CSV文件处理的基本配置。

        :param code: str，标的代码，如 "600000.SH" 或 "BTCUSDT"
        :param k_type: KL_TYPE 枚举值，K线数据类型，如日线（K_DAY）
        :param begin_time: str，开始日期，格式为 "YYYY-MM-DD" 或其他支持的格式
        :param end_time: str，结束日期，格式为 "YYYY-MM-DD" 或其他支持的格式
        :param autype: str，复权类型（默认不使用）
        :param file_path: str，CSV 文件的完整路径。如果未提供，将根据 `code` 和当前文件位置构造路径
        """

        # 定义CSV文件中的列名
        self.columns = [
            DATA_FIELD.FIELD_TIME,  # 时间列
            DATA_FIELD.FIELD_TIMESTAMP,
            DATA_FIELD.FIELD_OPEN,  # 开盘价
            DATA_FIELD.FIELD_HIGH,  # 最高价
            DATA_FIELD.FIELD_LOW,  # 最低价
            DATA_FIELD.FIELD_CLOSE,  # 收盘价
            DATA_FIELD.FIELD_VOLUME,  # 成交量
            # 可以根据需要添加其他列，如成交额、换手率等
            # DATA_FIELD.FIELD_TURNOVER,
            # DATA_FIELD.FIELD_TURNRATE,
        ]

        # 获取时间戳列的索引，便于后续过滤
        self.timestamp_idx = self.columns.index(DATA_FIELD.FIELD_TIMESTAMP)
        # 获取时间列的索引，便于后续判断数据的时间范围
        self.time_idx = self.columns.index(DATA_FIELD.FIELD_TIME)

        # 调用父类的初始化方法，传入相关参数
        super(CSV_API, self).__init__(code, k_type, begin_time, end_time, autype)
        self.headers_exist = True  # 第一行是否是标题，如果是数据，设置为False

        # 尝试将 begin_time 字符串转换为 datetime 对象，如果 begin_time 为空，则设置为 None
        try:
            self.begin_time = (
                datetime.strptime(begin_time, "%Y-%m-%d") if begin_time else None
            )
        except ValueError as ve:
            # 如果转换失败，捕获 ValueError 异常
            # 抛出 CChanException 异常，并附带错误信息和自定义错误代码
            raise CChanException(
                # 错误信息说明 begin_time 格式无效，并展示用户提供的日期
                f"Invalid begin_time format: {begin_time}. Expected 'YYYY-MM-DD'.",
                # 自定义错误代码，用于标识是日期格式错误
                ErrCode.INVALID_DATE_FORMAT,
            ) from ve  # 使用 'from ve' 保留原始异常堆栈信息

        # 尝试将 end_time 字符串转换为 datetime 对象，如果 end_time 为空，则设置为 None
        try:
            self.end_time = (
                datetime.strptime(end_time, "%Y-%m-%d") if end_time else None
            )
        except ValueError as ve:
            # 如果转换失败，捕获 ValueError 异常
            # 抛出 CChanException 异常，并附带错误信息和自定义错误代码
            raise CChanException(
                # 错误信息说明 end_time 格式无效，并展示用户提供的日期
                f"Invalid end_time format: {end_time}. Expected 'YYYY-MM-DD'.",
                # 自定义错误代码，用于标识是日期格式错误
                ErrCode.INVALID_DATE_FORMAT,
            ) from ve  # 使用 'from ve' 保留原始异常堆栈信息

        # 如果 file_path 没有传入，则自动生成默认路径
        if file_path is None:
            try:
                # 获取当前文件目录
                current_file_dir = os.path.dirname(os.path.realpath(__file__))
                # 获取当前文件目录的父目录
                base_dir = os.path.dirname(current_file_dir)
                # 获取父目录的父目录
                parent_dir = os.path.dirname(base_dir)
                # 在父目录的父目录中创建 Data 文件夹，并加入 code 和 k_type.name
                self.file_path = os.path.join(
                    parent_dir, "Data", self.code, self.k_type.name
                )
            except Exception as e:
                print(f"Error setting file_path: {e}")
                raise
        else:
            self.file_path = file_path

    def get_kl_data(self):
        """
        从CSV文件中读取K线数据，根据指定的时间范围过滤，并将每行数据解析为 CKLine_Unit 对象。
        :yield: CKLine_Unit 对象，每次返回一条K线数据
        """

        # 生成文件名
        filename = f"{self.code.replace('/', '_')}_{self.k_type.name}.csv"
        full_path = os.path.join(self.file_path, filename)
        oneDayTimestamp = int(86400000)

        # 如果CSV文件不存在，抛出异常
        if not os.path.exists(full_path):
            raise CChanException(
                f"file not exist: {full_path}", ErrCode.SRC_DATA_NOT_FOUND
            )

        # 计算时间戳（毫秒）
        begin_timestamp_ms = (
            int(self.begin_time.timestamp() * 1000) if self.begin_time else None
        )
        end_timestamp_ms = (
            int(self.end_time.timestamp() * 1000) + oneDayTimestamp
            if self.end_time
            else None
        )

        kl_units = []

        # 逐行读取CSV文件内容
        with open(full_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for line_number, row in enumerate(reader):
                # 如果第一行为表头，并且当前行为第一行，则跳过
                if self.headers_exist and line_number == 0:
                    continue

                # 如果数据长度与预期的列数不一致，抛出异常
                if len(row) != len(self.columns):
                    raise CChanException(
                        f"file format error: {full_path}",
                        ErrCode.SRC_DATA_FORMAT_ERROR,
                    )

                # 提取时间戳字段并转换为整数
                try:
                    current_timestamp_ms = int(row[self.timestamp_idx])
                    current_time = row[self.time_idx]
                except ValueError as ve:
                    print(
                        f"时间戳解析错误: {row[self.timestamp_idx]}，跳过第 {line_number} 行"
                    )
                    continue

                # 如果指定了开始时间，并且当前数据时间戳小于开始时间戳，则跳过该条数据
                if (
                    self.begin_time is not None
                    and current_timestamp_ms < begin_timestamp_ms
                ):
                    # print(f"当前时间{current_time}小于开始时间，跳过第 {line_number} 行")
                    continue

                # 如果指定了结束时间，并且当前数据时间戳大于结束时间戳，则跳过该条数据
                if (
                    self.end_time is not None
                    and current_timestamp_ms > end_timestamp_ms
                ):
                    # print(f"当前时间{current_time}大于结束时间，跳过第 {line_number} 行")
                    continue

                # 将每行数据转换为 CKLine_Unit 对象，并添加到列表中
                try:
                    kl_unit = CKLine_Unit(create_item_dict(row, self.columns))
                    kl_units.append(kl_unit)
                    # print(f"当前时间{current_time}符合，成功创建第 {line_number} 行")
                except CChanException as ce:
                    print(f"CKLine_Unit 创建错误: {ce}，跳过第 {line_number} 行")
                    continue

        # 按时间升序排序
        kl_units.sort(key=lambda klu: klu.timestamp)  # 假设 klu.time.ts 是时间戳

        # 生成排序后的K线数据
        for klu in kl_units:
            yield klu

    # 空方法，用于设置基础信息，留待子类重写或扩展
    def SetBasciInfo(self):
        pass

    # 类方法：初始化类（留待具体实现）
    @classmethod
    def do_init(cls):
        pass

    # 类方法：关闭类（留待具体实现）
    @classmethod
    def do_close(cls):
        pass
