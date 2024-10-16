from datetime import datetime, timedelta


class CTime:
    def __init__(self, year, month, day, hour, minute, second=0, auto=False):
        """
        初始化 CTime 类的实例。

        :param year: 年份
        :param month: 月份
        :param day: 日期
        :param hour: 小时
        :param minute: 分钟
        :param second: 秒，默认为0
        :param auto: 是否自适应对天的理解，默认为 False
        """
        self.year = year
        self.month = month
        self.day = day
        self.hour = hour
        self.minute = minute
        self.second = second
        self.auto = auto  # 自适应对天的理解
        self.set_timestamp()  # 设置时间戳

    def __str__(self):
        """
        返回 CTime 对象的字符串表示。

        :return: 格式为 "YYYY/MM/DD" 或 "YYYY/MM/DD HH:MM" 的字符串
        """
        if self.hour == 0 and self.minute == 0:
            return f"{self.year:04}/{self.month:02}/{self.day:02}"
        else:
            return f"{self.year:04}/{self.month:02}/{self.day:02} {self.hour:02}:{self.minute:02}:{self.second:02}"

    def to_str(self):
        """
        返回 CTime 对象的字符串表示（与 __str__ 方法相同）。

        :return: 格式为 "YYYY/MM/DD" 或 "YYYY/MM/DD HH:MM" 的字符串
        """
        return self.__str__()

    def toDateStr(self, splt=""):
        """
        将日期转换为字符串，格式为 "YYYYMMDD" 或 "YYYYMMDD" 中间用指定分隔符。

        :param splt: 分隔符，默认为空字符串
        :return: 日期字符串
        """
        return f"{self.year:04}{splt}{self.month:02}{splt}{self.day:02}"

    def toDate(self):
        """
        返回一个 CTime 对象，表示当前对象的日期部分（时间为00:00）。

        :return: CTime 对象
        """
        return CTime(self.year, self.month, self.day, 0, 0, auto=False)
    

    def to_datetime(self):
        """
        将 CTime 对象转换为 datetime 对象。
        
        :return: datetime 对象
        """
        return datetime(self.year, self.month, self.day, self.hour, self.minute, self.second)

    def set_timestamp(self):
        """
        设置时间戳（ts），用于比较两个 CTime 对象。
        当小时和分钟均为0且 auto 为 True 时，时间戳为前一天的23:59。
        """
        if self.hour == 0 and self.minute == 0 and self.auto:
            date = datetime(self.year, self.month, self.day, 23, 59, self.second)
        else:
            date = datetime(
                self.year, self.month, self.day, self.hour, self.minute, self.second
            )
        self.ts = int(date.timestamp() * 1000)

    def __gt__(self, other):
        if isinstance(other, datetime):
            return self.ts > int(other.timestamp() * 1000)
        elif isinstance(other, CTime):
            return self.ts > other.ts
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, datetime):
            return self.ts < int(other.timestamp() * 1000)
        elif isinstance(other, CTime):
            return self.ts < other.ts
        return NotImplemented

    def __add__(self, other):
        """
        实现两个 CTime 对象的加法。

        :param other: 另一个 CTime 对象
        :return: 新的 CTime 对象，表示加法结果
        """
        if isinstance(other, CTime):
            total_seconds = self.ts + other.ts
            return CTime.milliseconds_to_time(total_seconds)
        raise TypeError(
            "Unsupported operand type(s) for +: 'CTime' and '{}'".format(type(other))
        )

    def __sub__(self, other):
        """
        实现两个 CTime 对象的减法。

        :param other: 另一个 CTime 对象
        :return: 新的 CTime 对象，表示减法结果
        """
        if isinstance(other, CTime):
            total_seconds = self.ts - other.ts
            # print(f"Subtracting timestamps: {self} - {other} = {total_seconds}")
            return CTime.milliseconds_to_time(total_seconds)
        raise TypeError(
            "Unsupported operand type(s) for -: 'CTime' and '{}'".format(type(other))
        )

    @classmethod
    def milliseconds_to_time(cls, milliseconds):
        # 将毫秒转换为秒
        seconds = milliseconds / 1000.0
        # 使用timedelta来表示时间差
        time_delta = timedelta(seconds=seconds)
        # 将时间差转换为日期时间格式
        total_seconds = int(time_delta.total_seconds())
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        # 格式化输出
        time_str = f"{days}天 {hours}小时 {minutes}分钟 {int(seconds)}秒"
        return time_str
