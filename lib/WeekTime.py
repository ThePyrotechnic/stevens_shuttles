import datetime
from numbers import Real


class WeekTime:
    def __init__(self, hour: int = 0, minute: int = 0, second: int = 0):
        """Represents a moment of time within a seven-day week, starting at 00:00:00 on Monday"""
        self._hour = hour
        self._minute = minute
        self._second = second

    @property
    def hour(self):
        """The hour in the week that this WeekTime occurs on. From 0 to 167 inclusive"""
        return self._hour

    @property
    def minute(self):
        """The minute in the hour that this WeekTime occurs on"""
        return self._minute

    @property
    def second(self):
        """The second in the minute that this WeekTime occurs on"""
        return self._second

    @classmethod
    def from_timestamp(cls, timestamp: Real):
        """
        Convert a UTC timestamp in seconds to a WeekTime
        :param timestamp: The UTC timestamp, in seconds since the epoch
        :return: A WeekTime occurring at the same moment in the week as the given timestamp
        """
        utc = datetime.datetime.utcfromtimestamp(float(timestamp))
        return cls(utc.weekday() * 24 + utc.time().hour, utc.time().minute, utc.time().second)

    @classmethod
    def time_to_weektime(cls, time: datetime.time, weekday: int):
        """
        Convert a datetime.time to a WeekTime
        :param time: The datetime.time to convert
        :param weekday: The weekday that his time occurs on (0 through 6 (Monday - Sunday))
        :return: A WeekTime occurring on the given weekday at the same time as the given datetime.time
        """
        return cls(weekday * 24 + time.hour, time.minute, time.second)

    def __repr__(self):
        return f'<WeekTime: h:{self.hour} m:{self.minute} s:{self.second}>'
