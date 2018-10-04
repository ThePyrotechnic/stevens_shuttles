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


class Schedule:
    """Represents a paper schedule"""
    def __init__(self, route_id: int, schedule_columns: Dict[int, List[datetime.time]], valid_days: Set[str],
                 duration: Tuple[datetime.datetime, datetime.datetime]):
        self.route_id = route_id
        self.schedule_columns = schedule_columns
        self.valid_days = valid_days
        self.duration = duration

    def __str__(self):
        # Get arbitrary value from the dict of time lists and compute the length
        loop_count = len(next(iter(self.schedule_columns.values())))
        return f'{self.route_id}: {len(self.schedule_columns)} columns, {loop_count} loops, valid {self.duration[0]}-{self.duration[1]} {self.valid_days}'


class ScheduleManager:
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

        self._agency_id = agency_id
        self._schedules_path = schedules_path
        self._last_route_data = self.stops_by_route(update=True)
        self._last_paper_schedules = self.paper_schedules(update=True)
        self._shuttle_data = {}
        self._tz = pytz.timezone(local_timezone)

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

    def get_nearest_time(self, route_id: int, time: datetime.datetime, stop_id: int) -> datetime.datetime:
        """
        Get the closest time to the given time from the schedule for the given route and stop
        :param route_id: The route to get the stop schedules from
        :param time: The time to compare to the schedules
        :param stop_id: The stop to get the timetable for
        :return: A datetime representing the time closest to the given time, satisfying the conditions above
        :raises UnknownRoute: if the route could not be found
        """
        self._paper_schedules_lock.acquire()
        try:
            schedules = self._last_paper_schedules[route_id]
        except KeyError:
            raise UnknownRoute(f'No schedule associated with route {route_id}')
        self._paper_schedules_lock.release()

        day = datetime.datetime.now().weekday()
        possible_schedules = [s for s in schedules if day in s.valid_days]
        for schedule in possible_schedules:
            between = schedule.duration[0] <= time <= schedule.duration[1]
            if between:
                try:
                    timetable = schedule.schedule_columns[stop_id]
                    for stop_time in timetable:

                except KeyError:
                    raise UnknownStop(f'Stop {stop_id} not found in route {route_id}')
                break
            else:
                # TODO get the nearest time from the beginning/end of the timetable
                pass

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
                        last = self.datetime_to_utc(datetime.datetime.combine(today, datetime.datetime.strptime(line[0], '%I:%M%p').time()))
                        for time in line:
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
                    start_time = datetime.datetime.combine(today, datetime.datetime.strptime(start_time, '%I.%M%p').time())
                    end_time = datetime.datetime.combine(today, datetime.datetime.strptime(end_time, '%I.%M%p').time())

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
