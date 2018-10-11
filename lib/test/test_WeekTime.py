import datetime
import random
import os

from WeekTime import WeekTime


class TestWeekTime:
    def test_conversion(self):
        # Every hour for a 1 week period in october (monday through sunday)
        for day, weekday in zip(range(8, 15), range(7)):
            for hour in range(24):
                minute = random.randrange(0, 60)
                second = random.randrange(0, 60)
                fixed_time = datetime.datetime(year=2018, month=10, day=day,
                                               hour=hour, minute=minute, second=second,
                                               tzinfo=datetime.timezone.utc)
                week_time = WeekTime.from_timestamp(fixed_time.timestamp())
                assert week_time.hour == weekday * 24 + hour and week_time.minute == minute and week_time.second == second

    def test_time_conversion(self):
        for weekday in range(7):
            for hour in range(24):
                for minute in range(60):
                    for second in range(60):
                        time = datetime.time(hour=hour, minute=minute, second=second)
                        week_time = WeekTime.time_to_weektime(time, weekday)
                        assert week_time.hour == weekday * 24 + hour and week_time.minute == minute and week_time.second == second

    def test_lt(self):
        t1 = WeekTime(0, 0, 0)
        t2 = WeekTime(0, 0, 1)
        assert t1 < t2
        t1 = WeekTime(0, 0, 1)
        t2 = WeekTime(0, 1, 0)
        assert t1 < t2
        t1 = WeekTime(0, 1, 1)
        t2 = WeekTime(1, 0, 0)
        assert t1 < t2

    def test_gt(self):
        t1 = WeekTime(0, 0, 0)
        t2 = WeekTime(0, 0, 1)
        assert t2 > t1
        t1 = WeekTime(0, 0, 1)
        t2 = WeekTime(0, 1, 0)
        assert t2 < t1
        t1 = WeekTime(0, 1, 1)
        t2 = WeekTime(1, 0, 0)
        assert t2 < t1

    def test_eq(self):
        t1 = WeekTime(0, 0, 1)
        t2 = WeekTime(0, 0, 1)
        assert t1 == t2
        t1 = WeekTime(0, 1, 0)
        t2 = WeekTime(0, 1, 0)
        assert t1 == t2
        t1 = WeekTime(1, 0, 0)
        t2 = WeekTime(1, 0, 0)
        assert t1 == t2
        t1 = WeekTime(1, 1, 1)
        t2 = WeekTime(1, 1, 1)
        assert t1 == t2

    def test_ne(self):
        t1 = WeekTime(0, 0, 0)
        t2 = WeekTime(0, 0, 1)
        assert t2 != t1
        t1 = WeekTime(0, 0, 1)
        t2 = WeekTime(0, 1, 0)
        assert t2 != t1
        t1 = WeekTime(0, 1, 1)
        t2 = WeekTime(1, 0, 0)
        assert t2 != t1
