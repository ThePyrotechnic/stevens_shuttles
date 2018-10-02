import datetime
import json
from itertools import cycle


def main():
    for filename in ['red_weekday.json']:
        with open(filename) as cfg_file:
            cfg = json.load(cfg_file)
        print('-' * len(filename))
        print(filename)
        print('-' * len(filename))
        for cur_cfg in cfg:
            end_time = datetime.datetime.strptime(cur_cfg[0]['end_time'], '%I:%M%p')
            column_start_times = [datetime.datetime.strptime(c['start_time'], '%I:%M%p') for c in cur_cfg]
            column_patterns = [cycle(c['pattern']) for c in cur_cfg]
            column_firsts = [True for _ in cur_cfg]
            while column_start_times[0] != end_time:
                for count, column in enumerate(cur_cfg):
                    pattern = column_patterns[count]
                    if not column_firsts[count]:
                        column_start_times[count] += datetime.timedelta(minutes=pattern.__next__())
                    column_firsts[count] = False
                    print(column_start_times[count].time().strftime('%I:%M%p'), end=' ')
                print()
            print()


if __name__ == '__main__':
    main()
