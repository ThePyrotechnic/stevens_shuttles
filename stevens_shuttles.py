from configparser import ConfigParser
import logging
import os
import sys
import threading
import time

import psycopg2

import ScheduleManager
import ShuttleService


def parse_config(file: str = 'database.ini', db_type: str = 'postgresql'):
    parser = ConfigParser()
    parser.read(file)

    data = {}
    params = parser.items(db_type)
    for param in params:
        data[param[0]] = param[1]
    return data


def process_shuttle(scheduler: ScheduleManager.ScheduleManager, shuttle: ShuttleService.Shuttle, db: psycopg2):
    stops_by_route = scheduler.stops_by_route()
    try:
        stops = stops_by_route[shuttle.route_id]
    except KeyError:
        print(f'unknown route {shuttle.route_id}')
        return
    for stop in stops:
        if stop.at_stop(shuttle.position, 30) and scheduler.validate_stop(shuttle.id, stop.id):
            nearest_time = scheduler.get_nearest_time(shuttle.route_id, stop.id, shuttle.timestamp)
            with db.cursor() as cur:
                cur.execute('INSERT INTO "ConfirmedStop" (shuttle, route, stop, arrival_time, expected_time) VALUES (%s, %s, %s, %s, %s)',
                            (shuttle.id, shuttle.route_id, stop.id, shuttle.timestamp, nearest_time))
            logging.info(msg=(f'{threading.get_ident()}:{scheduler.get_route_name(shuttle.route_id)}\n'
                              f'\tShuttle ID {shuttle.id} stopped at ({stop.name}) at {shuttle.timestamp}. Nearest time in table: {nearest_time}'))
            break


def main():
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(levelname)s:%(message)s')

    db: psycopg2 = psycopg2.connect(**parse_config())
    db.set_session(autocommit=True)

    sm = ShuttleService.ShuttleManager(307)
    scheduler: ScheduleManager.ScheduleManager = ScheduleManager.ScheduleManager(307, os.path.join(os.getcwd(), 'schedules', 'generated'),
                                                                                 'America/New_York')

    while True:
        for shuttle in sm.shuttles():
            threading.Thread(target=process_shuttle, args=(scheduler, shuttle, db)).start()
        time.sleep(1 - (time.time() % 1))


if __name__ == '__main__':
    main()
