from multiprocessing import Process
import os
from configparser import ConfigParser
from typing import List
import time

import psycopg2

import ShuttleService
import ScheduleManager


def parse_config(file: str ='database.ini', db_type: str ='postgresql'):
    parser = ConfigParser()
    parser.read(file)

    data = {}
    params = parser.items(db_type)
    for param in params:
        data[param[0]] = param[1]
    return data


def process_shuttle(scheduler: ScheduleManager.ScheduleManager, shuttle: ShuttleService.Shuttle):
    # db: psycopg2 = psycopg2.connect(**parse_config())
    # TODO check whether shuttle has passed a stop and record it in the DB
    print(scheduler.get_route_name(shuttle.route_id))
    stops_by_route = scheduler.stops_by_route()
    try:
        stops = stops_by_route[shuttle.route_id]
        for stop in stops:
            if stop.at_stop(shuttle.position, 30):
                if scheduler.validate_stop(shuttle.id, stop.id):
                    # TODO add confirmed stop to DB
                    print(f'\tShuttle ID {shuttle.id} stopped at {stop.name} at {shuttle.timestamp}')
    except KeyError:
        print('unknown route')
        # TODO add unknown route to DB
        pass
    # db.close()


def main():
    sm = ShuttleService.ShuttleManager(307)
    debug_scheduler = ScheduleManager.ScheduleManager(307, os.path.join(os.getcwd(), 'schedules', 'generated'))
    # print(debug_scheduler._known_routes)
    with ScheduleManager.SharedScheduleManager() as manager:
        scheduler: ScheduleManager.ScheduleManager = manager.ScheduleManager(307, os.path.join(os.getcwd(), 'schedules', 'generated'))
        workers: List[Process] = []
        while True:
            for shuttle in sm.shuttles:
                p = Process(target=process_shuttle, args=(scheduler, shuttle))
                p.start()
                workers.append(p)
            time.sleep(2 - (time.time() % 2))


if __name__ == '__main__':
    main()
