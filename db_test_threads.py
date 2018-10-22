import threading
import os
from configparser import ConfigParser
import time
import logging
import sys

import psycopg2

import ScheduleManager
import MockShuttle as mockShuttle


def parse_config(file: str = 'database.ini', db_type: str = 'postgresql'):
    parser = ConfigParser()
    parser.read(file)

    data = {}
    params = parser.items(db_type)
    for param in params:
        data[param[0]] = param[1]
    return data


def mock_process_shuttle(scheduler: ScheduleManager.ScheduleManager, shuttle: mockShuttle.MockShuttle, db: psycopg2):
    start_t = time.time()
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
            with db.cursor() as cur:
                cur.execute('INSERT INTO "ConfirmedStop" (shuttle, route, stop, arrival_time, expected_time) VALUES (%s, %s, %s, %s, %s)',
                            (shuttle.id, shuttle.route_id, stop.id, shuttle.timestamp, nearest_time))
            logging.info(msg=(f'{threading.get_ident()}:{scheduler.get_route_name(shuttle.route_id)}\n'
                              f'\tShuttle ID {shuttle.id} stopped at ({stop.name}) at {shuttle.timestamp}. Nearest time in table: {nearest_time}\n'
                              f'\t{time.time() - start_t:.2f}'))
            break


def main():
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(levelname)s:%(message)s')

    db: psycopg2 = psycopg2.connect(**parse_config())
    db.set_session(autocommit=True)

    sm = mockShuttle.MockShuttleManager(307)
    scheduler: ScheduleManager.ScheduleManager = ScheduleManager.ScheduleManager(307, os.path.join(os.getcwd(), 'schedules', 'generated'),
                                                                                 'America/New_York')

    while True:
        for shuttle in sm.shuttles():
            threading.Thread(target=mock_process_shuttle, args=(scheduler, shuttle, db)).start()
        time.sleep(1 - (time.time() % 1))


if __name__ == '__main__':
    main()
