import datetime
import json
from itertools import cycle
import os


def main():
    for filename in ['red_weekday.json', 'red_morning.json', 'red_sunday.json', 'red_saturday.json',
                     'green_weekday.json',
                     'gray_weekday.json', 'gray_night.json',
                     'blue_weekday.json']:
        with open(os.path.join(os.getcwd(), filename)) as cfg_file:
            cfg = json.load(cfg_file)
        data = cfg['data']
        info = cfg['info']
        print('-' * len(filename))
        print(filename)
        if info.get('comment'):
            print(info['comment'])
        print('-' * len(filename))
        day_map = {0: 'Sun', 1: 'Mon', 2: 'Tues', 3: 'Wed', 4: 'Thurs', 5: 'Fri', 6: 'Sat'}
        valid_days = '_'.join([day_map[day] for day in info['valid_days']])
        duration = f'{info["valid_duration"][0]}_{info["valid_duration"][1]}'.replace(':', '.')
        generated_filename = os.path.join(os.getcwd(), 'generated', f'{info["route_id"]}_{duration}_{valid_days}.csv')
        with open(generated_filename, 'w') as out_file:
            print(*info['headers'], sep=',', file=out_file)
            for cur_cfg in data:
                if cur_cfg.get('manual'):
                    print(*cur_cfg['manual'], sep=',', file=out_file)
                    continue
                start_time = datetime.datetime.strptime(cur_cfg['start_time'], '%I:%M%p')
                end_time = datetime.datetime.strptime(cur_cfg['end_time'], '%I:%M%p')
                col_count = len(cur_cfg['spacing']) + 1
                column_start_times = [start_time]
                column_start_times.extend([start_time + datetime.timedelta(minutes=s) for s in cur_cfg['spacing']])
                column_patterns = [cycle(cur_cfg['pattern']) for _ in range(col_count)]
                column_firsts = [True for _ in range(col_count)]
                while column_start_times[0].time() != end_time.time():
                    for count in range(col_count):
                        pattern = column_patterns[count]
                        if not column_firsts[count]:
                            column_start_times[count] += datetime.timedelta(minutes=pattern.__next__())
                        column_firsts[count] = False
                        end = '' if count == col_count - 1 else ','
                        print(column_start_times[count].time().strftime('%I:%M%p'), end=end, file=out_file)
                    print(file=out_file)


if __name__ == '__main__':
    main()
