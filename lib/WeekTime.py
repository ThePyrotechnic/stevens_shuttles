import datetime


class WeekTime:

    def __new__(cls, hour=0, minute=0, second=0, microsecond=0):
        """
        WeekTime(hour, minute, second)
        """
        self = object.__new__(cls)
        self._hour = hour
        self._minute = minute
        self._second = second
        return self

    @property
    def hour(self):
        """hour (0-167)"""
        return self._hour

    @property
    def minute(self):
        """minute (0-59)"""
        return self._minute

    @property
    def second(self):
        """second (0-59)"""
        return self._second

    @classmethod
    def fromtimestamp(cls, t):
        utc = datetime.datetime.utcfromtimestamp(float(t)/1000)
        return cls(utc.weekday()*24+utc.time().hour, utc.time().minute, utc.time().second)

    @classmethod
    def fromweekday(cls, weekday, time):
        """Return WeekTime"""
        return cls(weekday*24+time.hour, time.minute, time.second)
