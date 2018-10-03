import os
import csv
import datetime
from itertools import cycle
from collections import defaultdict
from typing import Dict, Tuple, List
from multiprocessing import Lock
from multiprocessing.managers import BaseManager

import ShuttleService


class UnknownRoute(Exception):
    pass


class NoMoreTimes(Exception):
    pass


class Schedule:
    """Represents a paper schedule"""
    def __init__(self, route_id: int, schedule_columns: Dict[int, List[str]], valid_days: str, duration: Tuple[datetime.time, datetime.time]):
        self.route_id = route_id
        self.schedule_columns = schedule_columns
        # TODO Come up with a better way of classifying schedule date validity
        self.is_midweek = valid_days == 'weekdays'
        self.duration = duration

    def __str__(self):
        # Get any value from the dict of time lists and compute the length
        loop_count = len(next(iter(self.schedule_columns.values())))
        return f'{self.route_id}: {len(self.schedule_columns)} columns, {loop_count} loops, valid {self.duration[0]}-{self.duration[1]} {self.valid_days}'


class ScheduleManager:
    def __init__(self, agency_id: int, schedules_path: str):
        """
        Manages all routing and scheduling and determines the timeliness of a shuttle
        :param agency_id: The agency for which to compute scheduling
        :param schedules_path: The path where the CSVs of the schedules are stored
        """
        self._shuttle_data_lock = Lock()
        self._route_data_lock = Lock()
        self._paper_schedules_lock = Lock()

        self._agency_id = agency_id
        self._schedules_path = schedules_path
        self._last_route_data = self.stops_by_route(update=True)
        self._last_paper_schedules = self.paper_schedules(update=True)
        self._shuttle_data = {}

        routes = ShuttleService.ShuttleService(self._agency_id).get_routes()
        self._known_routes = {route.id: route.long_name for route in routes}

    def get_route_name(self, route_id):
        """
        Get the route name for a given route ID, if possible
        :param route_id: The route ID to look for
        :return: The route name if it can be found, else None
        """
        return self._known_routes.get(route_id)

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

    def get_nearest_time(self, route_id: int, time: datetime.time):
        # TODO Remember that bus timestamps are in UTC but paper schedules are ET
        # TODO Think about handling friday past midnight for the blue line and other late-night lines
        self._paper_schedules_lock.acquire()
        day = datetime.datetime.now().weekday()
        is_midweek = day < 5
        for schedule in self._last_paper_schedules[route_id]:
            # TODO Get the currently valid schedule for the route
            pass
        self._paper_schedules_lock.release()

    def paper_schedules(self, update: bool = False) -> Dict[int, List[Schedule]]:
        """
        Load paper schedules from the schedule directory
        :param update: Whether to return the last computed data or reload the schedules from the disk
        :return: A dictionary mapping schedule route IDs to a list of schedules for that stop
        """
        self._paper_schedules_lock.acquire()
        if update:
            schedules = defaultdict(list)
            for schedule_file in os.listdir(self._schedules_path):
                with open(os.path.join(self._schedules_path, schedule_file)) as schedule:
                    data = csv.reader(schedule)
                    header = [int(col) for col in data.__next__()]
                    schedule_cols = {col: [] for col in header}
                    next_header = cycle(header)
                    for line in data:
                        for time in line:
                            schedule_cols[next_header.__next__()].append(time)

                    schedule_name = str(os.path.splitext(os.path.split(schedule.name)[1])[0])
                    route_id, start_time, end_time, valid_days = schedule_name.split('_')
                    start_time = datetime.datetime.strptime(start_time, '%I.%M%p').time()
                    end_time = datetime.datetime.strptime(end_time, '%I.%M%p').time()

                    schedules[int(route_id)].append(Schedule(route_id, schedule_cols, valid_days, (start_time, end_time)))
            self._last_paper_schedules = schedules

        self._paper_schedules_lock.release()
        return self._last_paper_schedules


class SharedScheduleManager(BaseManager):
    """A manager for sharing the ScheduleManager class"""
    pass


SharedScheduleManager.register('ScheduleManager', ScheduleManager)
