import os
import csv
import datetime
from itertools import cycle
from collections import defaultdict
from typing import Dict, Tuple, List, Set
from multiprocessing import Lock
from multiprocessing.managers import BaseManager

import pytz

import ShuttleService


class UnknownRoute(Exception):
    pass


class UnknownStop(Exception):
    pass


class ScheduleException(Exception):
    pass


class Schedule:
    """Represents a paper schedule"""

    def __init__(self, route_id: int, schedule_columns: Dict[int, List[datetime.datetime]], valid_days: Set[str],
                 duration: Tuple[datetime.datetime, datetime.datetime]):
        self.route_id = route_id
        self.schedule_columns = schedule_columns

        day_map = {'Sun': 7, 'Mon': 0, 'Tues': 1, 'Wed': 2, 'Thurs': 3, 'Fri': 4, 'Sat': 5}
        self.valid_days = [day_map[d] for d in valid_days]
        self.duration = duration

    def __str__(self):
        # Get the longest timetable length
        loop_count = max([len(t) for t in self.schedule_columns.values()])
        return f'{self.route_id}: {len(self.schedule_columns)} columns, {loop_count} loops, valid {self.duration[0]}-{self.duration[1]} {self.valid_days}'


class ScheduleManager:
    OLD_DATE = datetime.datetime(day=1, month=1, year=1980)

    def __init__(self, agency_id: int, schedules_path: str, local_timezone: str):
        """
        Manages all routing and scheduling and determines the timeliness of a shuttle
        :param agency_id: The agency for which to compute scheduling
        :param schedules_path: The path where the CSVs of the schedules are stored
        :param local_timezone: A string representing the local timezone
        """
        self._shuttle_data_lock = Lock()
        self._route_data_lock = Lock()
        self._paper_schedules_lock = Lock()

        self._tz = pytz.timezone(local_timezone)

        self._agency_id = agency_id
        self._schedules_path = schedules_path
        self._last_route_data = self.stops_by_route(update=True)
        self._last_paper_schedules = self.paper_schedules(update=True)
        self._shuttle_data = {}

        routes = ShuttleService.ShuttleService(self._agency_id).get_routes()
        self._known_routes = {route.id: route.long_name for route in routes}

    def get_route_name(self, route_id: int):
        """
        Get the route name for a given route ID, if possible
        :param route_id: The route ID to look for
        :return: The route name
        :raise UnknownRoute: if the route could nto be identified
        """
        try:
            return self._known_routes[route_id]
        except KeyError:
            raise UnknownRoute(f'Route {route_id} is unknown')

    def stops_by_route(self, update: bool = False) -> Dict[int, List[ShuttleService.Stop]]:
        """
        Get the stops for each route active for the current shuttle service
        :param update: Whether to return the last computed data or fetch the latest data from the web
        :return: A dictionary mapping route IDs to lists of stops
        """
        self._route_data_lock.acquire()
        if update:
            ss = ShuttleService.ShuttleService(self._agency_id)
            stops = ss.get_stops()
            stop_dict = {}
            for stop in stops:
                stop_dict[stop.id] = stop

            stops_by_route = ss.get_stop_ids_for_routes()
            latest_route_data = {}
            for route in ss.get_routes():
                latest_route_data[route.id] = [stop_dict[s] for s in stops_by_route[route.id]]
            self._last_route_data = latest_route_data

        self._route_data_lock.release()
        return self._last_route_data

    def validate_stop(self, shuttle_id: int, stop_id: int):
        self._shuttle_data_lock.acquire()

        valid = False
        try:
            if self._shuttle_data[shuttle_id]['prev_stop'] != stop_id:
                self._shuttle_data[shuttle_id]['prev_stop'] = stop_id
                valid = True
        except KeyError:
            self._shuttle_data[shuttle_id] = {
                'prev_stop': stop_id
            }
            valid = True

        self._shuttle_data_lock.release()
        return valid

    def get_nearest_time(self, route_id: int, stop_id: int, reported_time: datetime.datetime) -> datetime.datetime:
        """
        Get the closest time to the given time from the schedule for the given route and stop
        :param route_id: The route to get the stop schedules from
        :param reported_time: The time to compare to the schedules
        :param stop_id: The stop to get the timetable for
        :return: A datetime representing the time closest to the given time, satisfying the conditions above
        :raises UnknownRoute: if the route ID could not be found
        :raises UnknownStop: if no timetable for the stop ID could be found
        """
        self._paper_schedules_lock.acquire()
        try:
            schedules = self._last_paper_schedules[route_id]
        except KeyError:
            raise UnknownRoute(f'No schedule associated with route {route_id}')
        self._paper_schedules_lock.release()

        day = datetime.datetime.now().weekday()
        possible_schedules = sorted([s for s in schedules if day in s.valid_days], key=lambda s: s.duration[0])
        if len(possible_schedules) == 0:
            raise ScheduleException(f'No {datetime.datetime.now().strftime("%A")} schedules for route {route_id}')
        last_end_time = None
        for schedule in possible_schedules:
            if schedule.duration[0] <= reported_time <= schedule.duration[1]:
                try:
                    prev_time = None
                    timetable = schedule.schedule_columns[stop_id]
                    for stop_time in timetable:
                        if stop_time > reported_time and prev_time is not None:
                            return prev_time if reported_time - prev_time < stop_time - reported_time else stop_time
                        elif stop_time == reported_time:
                            return stop_time
                        prev_time = stop_time
                except KeyError:
                    raise UnknownStop(f'Stop {stop_id} not found in route {route_id}')
                break
            else:
                if reported_time < schedule.duration[0]:
                    if last_end_time is not None:
                        return last_end_time if reported_time - last_end_time < schedule.duration[0] - reported_time else schedule.duration[0]
                    else:
                        return schedule.duration[0]
                else:
                    last_end_time = schedule.duration[1]

    def paper_schedules(self, update: bool = False) -> Dict[int, List[Schedule]]:
        """
        Load paper schedules from the schedule directory
        :NOTE: Paper schedules MUST be regenerated at least every day or get_nearest_time WILL NOT WORK
        :param update: Whether to return the last computed data or reload the schedules from the disk
        :return: A dictionary mapping schedule route IDs to a list of schedules for that stop
        #TODO Someone who has the patience to deal with dates and timezones should review this
        """
        self._paper_schedules_lock.acquire()
        if update:
            schedules = defaultdict(list)
            today = datetime.date.today()
            tomorrow = today + datetime.timedelta(days=1)
            for schedule_file in os.listdir(self._schedules_path):
                with open(os.path.join(self._schedules_path, schedule_file)) as schedule:
                    data = csv.reader(schedule)
                    header = [int(col) for col in data.__next__()]
                    schedule_cols = {col: [] for col in header}
                    next_header = cycle(header)
                    for line in data:
                        # If a time is None it will be ignored
                        first = [t for t in line if t != 'None'][0]
                        last = self.datetime_to_utc(datetime.datetime.combine(today, datetime.datetime.strptime(first, '%I:%M%p').time()))
                        for time in line:
                            if time == 'None':
                                # If a time is marked as None, go to the next header but add nothing to the current timetable
                                next_header.__next__()
                                continue
                            # Convert all schedule strings from the local timezone to UTC
                            time = self.datetime_to_utc(datetime.datetime.combine(today, datetime.datetime.strptime(time, '%I:%M%p').time()))
                            # If a time has crossed midnight
                            if time < last:
                                time = datetime.datetime.combine(tomorrow, time.time())
                                today = tomorrow
                                tomorrow += datetime.timedelta(days=1)
                            last = time
                            schedule_cols[next_header.__next__()].append(time)

                    schedule_name = str(os.path.splitext(os.path.split(schedule.name)[1])[0])
                    route_id, start_time, end_time, *valid_days = schedule_name.split('_')

                    # Every schedule's time ranges should be assumed to be the current day
                    # and the next day if the range extends past midnight
                    # see ScheduleManger.get_nearest_time for how this is used
                    today = datetime.date.today()
                    start_time = self.datetime_to_utc(datetime.datetime.combine(today, datetime.datetime.strptime(start_time, '%I.%M%p').time()))
                    end_time = self.datetime_to_utc(datetime.datetime.combine(today, datetime.datetime.strptime(end_time, '%I.%M%p').time()))

                    if end_time < start_time:
                        end_time += datetime.timedelta(days=1)

                    schedules[int(route_id)].append(Schedule(route_id, schedule_cols, set(valid_days), (start_time, end_time)))
            self._last_paper_schedules = schedules

        self._paper_schedules_lock.release()
        return self._last_paper_schedules

    def datetime_to_utc(self, dt: datetime.datetime) -> datetime.datetime:
        return self._tz.localize(dt).astimezone(pytz.utc)


class SharedScheduleManager(BaseManager):
    """A manager for sharing the ScheduleManager class"""
    pass


SharedScheduleManager.register('ScheduleManager', ScheduleManager)


if __name__ == '__main__':
    t = datetime.datetime.combine(datetime.date.today(), datetime.time(hour=17, minute=0, second=0, tzinfo=datetime.timezone(datetime.timedelta(seconds=0))))
    sched = ScheduleManager(307, os.path.join('C:\\', 'Users', 'micha', 'Documents', 'PycharmProjects', 'stevens_shuttles', 'schedules', 'generated'), 'America/New_York')
    res = sched.get_nearest_time(4004706, 4132090, t)
    pass
