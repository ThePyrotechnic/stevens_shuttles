import os
import csv
import datetime
import json
from itertools import cycle
from collections import defaultdict
from typing import Dict, List, TextIO
from multiprocessing import Lock
from multiprocessing.managers import BaseManager
from datetime import datetime

import pytz

import ShuttleService


class UnknownRoute(Exception):
    """The given route is unknown in the current context"""
    pass


class UnknownStop(Exception):
    """The given stop is unknown in the current context"""
    pass


class Schedule:

    def __init__(self, route_id: int, timetable: Dict[int, List[datetime]], valid_days: List[int], start_time: datetime, name: str = None):
        """
        A paper schedule
        :param route_id: The route ID that this schedule is valid for
        :param timetable: The timetable listing the times for each stop ID
        :param valid_days: The days for which this schedule is valid
        :param start_time: The earliest time in the schedule's timetable
        :param name: The name of the schedule
        """
        self.route_id = route_id
        self.start_time = start_time
        self.timetable = timetable
        self.valid_days = valid_days
        self.name = name

    def __str__(self):
        # Get the longest timetable length
        loop_count = max([len(t) for t in self.timetable.values()])
        return f'{self.name + ":" or ""} {self.route_id}: {len(self.timetable)} columns, {loop_count} loops'


class ScheduleManager:
    OLD_DATE = datetime(day=1, month=1, year=1980)

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
        :raise UnknownRoute: if the route could not be identified
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

    def validate_stop(self, shuttle_id: int, stop_id: int) -> bool:
        """
        Check whether the same shuttle was at this stop twice in a row
        :param shuttle_id: The ID of the shuttle to check
        :param stop_id: The stop ID to check for a double-stop
        :return: True if the shuttle was not at this stop twice in a row (or more), False otherwise
        """
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

    def get_nearest_time(self, route_id: int, stop_id: int, reported_time: datetime) -> datetime:
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
        # Order schedules by start time so that they are searched sequentially
        schedules = sorted(schedules, key=lambda s: s.start_time)
        for schedule in schedules:
            try:
                stop_times = schedule.timetable[stop_id]
            except KeyError:
                continue
            if reported_time < stop_times[0]:
                return stop_times[0]
            if reported_time > stop_times[-1]:
                continue
            # At this point the stop time must be within the current list of stop times
            prev_time = stop_times[0]
            for cur_time in stop_times[1:]:
                if reported_time <= cur_time:
                    if reported_time == cur_time:
                        return cur_time
                    # Return the closer time
                    return cur_time if cur_time - reported_time < reported_time - prev_time else prev_time
        raise UnknownStop(f'Stop ID {stop_id} not found in any schedule for route {route_id}')

    def paper_schedules(self, update: bool = False) -> Dict[int, List[Schedule]]:
        """
        Load paper schedules from the schedule directory
        :param update: Whether to return the last computed data or reload the schedules from the disk
        :return: A dictionary mapping schedule route IDs to a list of schedules for that stop
        """
        self._paper_schedules_lock.acquire()
        if update:
            schedules = defaultdict(list)
            with open(os.path.join(self._schedules_path, 'file_info.json'), 'r') as info_file:
                file_info = json.load(info_file)['file_info']
                for schedule_filename in [f for f in os.listdir(self._schedules_path) if os.path.splitext(f)[-1] == '.csv']:
                    with open(os.path.join(self._schedules_path, schedule_filename)) as schedule_file:
                        schedule = self._convert_schedule_file(file_info[schedule_filename], schedule_file, os.path.splitext(schedule_filename)[0])
                        schedules[schedule.route_id].append(schedule)
            self._last_paper_schedules = schedules

        self._paper_schedules_lock.release()
        return self._last_paper_schedules

    def _convert_schedule_file(self, file_info: Dict, schedule_file: TextIO, schedule_name) -> Schedule:
        """
        Convert a schedule file into a Schedule object
        :param file_info: The information about the file
        :param schedule_file: The opened file handle of the schedule
        :param schedule_name: The name of the schedule
        :return: A Schedule object representing the paper schedule
        """
        data = csv.reader(schedule_file)
        stops = [int(col) for col in data.__next__()]
        schedule_cols = {col: [] for col in stops}
        next_stop_id = cycle(stops)
        utcoffset_str = datetime.datetime.now(self._tz).strftime('%z')
        utcoffset = datetime.timedelta(hours=int(utcoffset_str[1:3]), minutes=int(utcoffset_str[3:5]))
        negative = utcoffset_str[0] == '-'

        found_start = False
        start_time = None
        for line in data:
            for str_time in line:
                if str_time.lower() == 'none':
                    next_stop_id.__next__()
                    continue
                obj_time = datetime.datetime.strptime(str_time, '%I:%M%p').time()
                for day in file_info['valid_days']:
                    week_time = WeekTime.time_to_weektime(obj_time, day)
                    if not found_start:
                        start_time = week_time
                    schedule_cols[next_stop_id.__next__()].append(week_time)
        for stop_id, timetable in schedule_cols.items():
            schedule_cols[stop_id] = sorted(schedule_cols[stop_id])
        return Schedule(file_info['route_id'], schedule_cols, file_info['valid_days'], start_time, name=schedule_name)


class SharedScheduleManager(BaseManager):
    """A manager for sharing the ScheduleManager class"""
    pass


SharedScheduleManager.register('ScheduleManager', ScheduleManager)
