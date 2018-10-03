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
    db: psycopg2 = psycopg2.connect(**parse_config())
    # TODO check whether shuttle has passed a stop and record it in the DB
    print(f'Processed shuttle {shuttle.id}|{shuttle.timestamp}')
    db.close()


def main():
    sm = ShuttleService.ShuttleManager(307)
    with ScheduleManager.SharedScheduleManager() as manager:
        scheduler: ScheduleManager.ScheduleManager = manager.ScheduleManager(307, os.path.join(os.getcwd(), 'schedules', 'generated'))
        workers: List[Process] = []
        for shuttle in sm.shuttles:
            p = Process(target=process_shuttle, args=(scheduler, shuttle))
            p.start()
            workers.append(p)
        for worker in workers:
                worker.join()
    pass


if __name__ == '__main__':
    main()
