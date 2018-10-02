import os
import csv
from datetime import datetime
from itertools import cycle
from collections import deque
from typing import Dict, Deque
from multiprocessing.managers import BaseManager

import ShuttleService


class UnknownRoute(Exception):
    pass


class NoMoreTimes(Exception):
    pass


class _ScheduleManager:
    def __init__(self, agency_id: int, schedules_path: str):
        self.agency_id = agency_id
        self.schedules_path = schedules_path
        self._last_route_data = self.route_data(update=True)
        self.paper_schedules = self._get_latest_paper_schedules()
        self._shuttle_data = {}

        routes = ShuttleService.ShuttleService(self.agency_id).get_routes()
        self.known_routes = {route.long_name: route.id for route in routes}

    def route_data(self, update: bool = False):
        if update:
            ss = ShuttleService.ShuttleService(self.agency_id)
            stops = ss.get_stops()
            stop_dict = {}
            for stop in stops:
                stop_dict[stop.id] = stop

            stops_by_route = ss.get_stop_ids_for_routes()
            latest_route_data = {}
            for route in ss.get_routes():
                latest_route_data[route.id] = [stop_dict[s].__dict__ for s in stops_by_route[route.id]]
            self._last_route_data = latest_route_data
            return latest_route_data
        return self._last_route_data

    def validate_stop(self, shuttle_id: int, stop_id: int):
        try:
            if self._shuttle_data[shuttle_id]['prev_stop'] == stop_id:
                return False
            self._shuttle_data[shuttle_id]['prev_stop'] = stop_id
            return True
        except KeyError:
            self._shuttle_data[shuttle_id] = {
                'prev_stop': stop_id
            }
            return True

    def get_next_stop_time(self, route_name: str, stop_id: int, peek: bool = False) -> str:
        try:
            route_id = self.known_routes[route_name]
            if peek:
                return self.paper_schedules[route_id][stop_id][0]
            return self.paper_schedules[route_id][stop_id].popleft()
        except KeyError:
            raise UnknownRoute(f'Unknown route name: {route_name}')
        except IndexError:
            raise NoMoreTimes(f'No more scheduled times for {route_name}:{stop_id}')

    def _get_latest_paper_schedules(self) -> Dict[int, Dict[int, Deque[str]]]:
        schedules = {}
        for schedule_file in os.listdir(self.schedules_path):
            with open(os.path.join(self.schedules_path, schedule_file)) as schedule:
                data = csv.reader(schedule)
                header = [int(col) for col in data.__next__()]
                schedule_cols = {col: deque() for col in header}
                next_header = cycle(header)
                for line in data:
                    for time in line:
                        schedule_cols[next_header.__next__()].append(time)
                schedules[int(os.path.split(schedule.name)[1].split('.')[0])] = schedule_cols
        return schedules


class SharedScheduleManager(BaseManager):
    pass


SharedScheduleManager.register('Schedule', _ScheduleManager)
