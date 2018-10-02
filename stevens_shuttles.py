from configparser import ConfigParser
from multiprocessing import Pool
from itertools import repeat
from typing import Dict

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


def process_shuttle(route_data: Dict, shuttle: ShuttleService.Shuttle):
    # TODO Check if shuttle is within scheduled route bounds
    return f'Processed shuttle {shuttle.id}|{shuttle.timestamp}, {len(route_data)}'


def get_latest_route_data():
    ss = ShuttleService.ShuttleService(307)
    stops = ss.get_stops()
    stop_dict = {}
    for stop in stops:
        stop_dict[stop.id] = stop

    stops_by_route = ss.get_stop_ids_for_routes()
    latest_route_data = {}
    for route in ss.get_routes():
        latest_route_data[route.id] = [stop_dict[s].__dict__ for s in stops_by_route[route.id]]
    return latest_route_data


def main():
    db: psycopg2 = psycopg2.connect(**parse_config())

    latest_route_data = get_latest_route_data()
    sm = ShuttleService.ShuttleManager(307)
    # TODO Send a copy of latest_route_data to workers along with the latest static schedule, and update periodically
    with Pool(5) as p:
        res = p.starmap_async(process_shuttle, zip(repeat(latest_route_data), sm.shuttles))
        print(res.get())
    db.close()
    pass


if __name__ == '__main__':
    main()
