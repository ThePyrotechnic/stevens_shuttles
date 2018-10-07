from multiprocessing import Process
import os
from configparser import ConfigParser
from typing import List, Tuple, Dict
import time
import random
import datetime
from itertools import cycle

import psycopg2

import ShuttleService
import ScheduleManager


class MockShuttle:
    STOPS_BY_ROUTE_ID = {4004706: [4211460, 4132090, 4208462], 4011456: [4208464, 4111538, 4211462, 4151398, 4220780, 4211464, 4211466, 4132090],
                         4011458: [4220778, 4220774, 4132090], 4011460: [4220776, 4151398, 4220780, 4211466, 4132090, 4208464, 4111538, 4211462, 4211464]}

    def __init__(self):
        self.id = random.randrange(100000, 200000)
        self.route_id = random.choice(list(MockShuttle.STOPS_BY_ROUTE_ID))
        self.timestamp = datetime.datetime.now().astimezone(datetime.timezone(datetime.timedelta(seconds=0)))

        self._stops = cycle(MockShuttle.STOPS_BY_ROUTE_ID[self.route_id])
        self._ss = ShuttleService.ShuttleService(307)
        pass

    @property
    def position(self) -> Tuple[float, float]:
        if random.random() < 0.10:
            return self._ss.get_stop(self._stops.__next__()).position
        else:
            return 40.737898, -74.037995

    def __str__(self):
        return f'ID: {self.id}, Route ID: {self.route_id}'


class MockShuttleManager(ShuttleService.ShuttleManager):
    def __init__(self, agency_id: int):
        super().__init__(agency_id)

    def shuttles(self, detailed: bool = False, key_filter: Dict = None) -> List[MockShuttle]:
        random_shuttles = []
        for _ in range(random.randrange(3, 6)):
            random_shuttles.append(MockShuttle())
        return random_shuttles


def mock_process_shuttle(scheduler: ScheduleManager.ScheduleManager, shuttle: MockShuttle):
    # db: psycopg2 = psycopg2.connect(**parse_config())
    print(scheduler.get_route_name(shuttle.route_id))
    stops_by_route = scheduler.stops_by_route()
    try:
        stops = stops_by_route[shuttle.route_id]
        for stop in stops:
            if stop.at_stop(shuttle.position, 30) and scheduler.validate_stop(shuttle.id, stop.id):
                try:
                    nearest_time = scheduler.get_nearest_time(shuttle.route_id, stop.id, shuttle.timestamp)
                except ScheduleManager.ScheduleException as e:
                    print(f'\t{e}')
                    return
                # TODO add confirmed stop to DB
                print(f'\tShuttle ID {shuttle.id} stopped at {stop.id} at {shuttle.timestamp}. Nearest time in table: {nearest_time}')
    except KeyError:
        print('unknown route')
        # TODO add unknown route to DB
        pass
    # db.close()
    pass


def main():
    sm = MockShuttleManager(307)

    # with ScheduleManager.SharedScheduleManager() as manager:
    #     scheduler: ScheduleManager.ScheduleManager = manager.ScheduleManager(307, os.path.join(os.getcwd(), '..', 'schedules', 'generated'),
    #                                                                          'America/New_York')
    scheduler: ScheduleManager.ScheduleManager = ScheduleManager.ScheduleManager(307, os.path.join(os.getcwd(), '..', 'schedules', 'generated'),
                                                                                 'America/New_York')

    while True:
        for shuttle in sm.shuttles():
            mock_process_shuttle(scheduler, shuttle)
        time.sleep(1 - (time.time() % 1))

        # workers: List[Process] = []
        # while True:
        #     for shuttle in sm.shuttles:
        #         p = Process(target=mock_process_shuttle, args=(scheduler, shuttle))
        #         p.start()
        #         workers.append(p)
        #     time.sleep(2 - (time.time() % 2))


if __name__ == '__main__':
    main()
