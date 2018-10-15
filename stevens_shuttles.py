from multiprocessing import Process
import os
from configparser import ConfigParser
import time

import psycopg2

import ShuttleService
import ScheduleManager


def parse_config(file: str = 'database.ini', db_type: str = 'postgresql'):
    parser = ConfigParser()
    parser.read(file)

    data = {}
    params = parser.items(db_type)
    for param in params:
        data[param[0]] = param[1]
    return data


def process_shuttle(scheduler: ScheduleManager.ScheduleManager, shuttle: ShuttleService.Shuttle):
    # db: psycopg2 = psycopg2.connect(**parse_config())
    print(scheduler.get_route_name(shuttle.route_id))
    stops_by_route = scheduler.stops_by_route()
    try:
        stops = stops_by_route[shuttle.route_id]
    except KeyError:
        print(f'unknown route {shuttle.route_id}')
        return
    for stop in stops:
        if stop.at_stop(shuttle.position, 30) and scheduler.validate_stop(shuttle.id, stop.id):
            nearest_time = scheduler.get_nearest_time(shuttle.route_id, stop.id, shuttle.timestamp)
            # TODO add confirmed stop to DB
            print(f'\tShuttle ID {shuttle.id} stopped at {stop} ({stop.name}) at {shuttle.timestamp}. Nearest time in table: {nearest_time}')
    # db.close()


def main():
    sm = ShuttleService.ShuttleManager(307)
    debug_scheduler = ScheduleManager.ScheduleManager(307, os.path.join(os.getcwd(), 'schedules', 'generated'), 'America/New_York')

    while True:
        for shuttle in sm.shuttles():
            process_shuttle(debug_scheduler, shuttle)
        time.sleep(2 - (time.time() % 2))

    # with ScheduleManager.SharedScheduleManager() as manager:
    #     scheduler: ScheduleManager.ScheduleManager = manager.ScheduleManager(307, os.path.join(os.getcwd(), 'schedules', 'generated'),
    #                                                                          'America/New_York')
    #     workers: List[Process] = []
    #     while True:
    #         for shuttle in sm.shuttles():
    #             p = Process(target=process_shuttle, args=(scheduler, shuttle))
    #             p.start()
    #             workers.append(p)
    #         time.sleep(2 - (time.time() % 2))


if __name__ == '__main__':
    main()
