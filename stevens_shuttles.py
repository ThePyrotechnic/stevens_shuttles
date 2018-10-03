from configparser import ConfigParser
import multiprocessing
import os

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


def process_shuttle(shuttle: ShuttleService.Shuttle):
    return f'Processed shuttle {shuttle.id}|{shuttle.timestamp}'


def main():
    db: psycopg2 = psycopg2.connect(**parse_config())

    sm = ShuttleService.ShuttleManager(307)
    with ScheduleManager.SharedScheduleManager() as manager:
        scheduler: ScheduleManager.ScheduleManager = manager.ScheduleManager(307, os.path.join(os.getcwd(), 'schedules', 'generated'))
        sched = scheduler.paper_schedules()
    with multiprocessing.Pool(8) as p:
        res = p.map_async(process_shuttle, sm.shuttles)
        print(res.get())
    db.close()
    pass


if __name__ == '__main__':
    main()
