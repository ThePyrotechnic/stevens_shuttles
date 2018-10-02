from configparser import ConfigParser
from itertools import cycle
import multiprocessing
import os
import csv

import psycopg2

import ShuttleService


def parse_config(file: str ='database.ini', db_type: str ='postgresql'):
    parser = ConfigParser()
    parser.read(file)

    data = {}
    params = parser.items(db_type)
    for param in params:
        data[param[0]] = param[1]
    return data


def process_shuttle(shuttle: ShuttleService.Shuttle):
    try:
        route_data = LATEST_ROUTE_DATA[shuttle.route_id]
    except KeyError:
        # TODO handle route not found
        pass

    return f'Processed shuttle {shuttle.id}|{shuttle.timestamp}, {len(LATEST_ROUTE_DATA)}'


LATEST_ROUTE_DATA = get_latest_route_data()
PAPER_SCHEDULES = get_paper_schedules()


def main():
    global LATEST_ROUTE_DATA
    db: psycopg2 = psycopg2.connect(**parse_config())

    LATEST_ROUTE_DATA = get_latest_route_data()
    sm = ShuttleService.ShuttleManager(307)

    m = multiprocessing.Manager()
    m.reg
    # TODO Send a copy of latest_route_data to workers along with the latest static schedule, and update periodically
    with multiprocessing.Pool(8) as p:
        res = p.map_async(process_shuttle, sm.shuttles)
        print(res.get())
    db.close()
    pass


if __name__ == '__main__':
    main()
