from configparser import ConfigParser
from multiprocessing import Pool

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
    # TODO Check if shuttle is within scheduled route bounds
    return f'Processed shuttle {shuttle.id}|{shuttle.timestamp}'


def main():
    db: psycopg2 = psycopg2.connect(**parse_config())

    sm = ShuttleService.ShuttleManager(307)

    # TODO Create in-memory shared schedule for process_shuttle to work with
    # TODO Create in-memory shared map of current route-stop relationships, update periodically
    with Pool(5) as p:
        print(p.map(process_shuttle, sm.shuttles))

    db.close()
    pass


if __name__ == '__main__':
    main()
