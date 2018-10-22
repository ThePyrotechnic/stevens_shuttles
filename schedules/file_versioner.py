import hashlib
import os

import requests


def main():
    base_url_1 = 'https://www.stevens.edu/sites/stevens_edu/files'
    base_url_2 = 'https://www.stevens.edu/sites/stevens_edu/files/files/ResLife'
    local_dir = 'schedules/originals/spring18'

    file_map = {
        'New Blue Line Fall 2018_0.tif',
        'New Green Line Fall 2018_0.tif',
        'red line morning .jpg',
        'Red Line Saturday.pdf',
        'Red Line Sunday.pdf',
        'Stevens Spring 2018 Gray line'
    }

    os.mkdir(os.path.join(local_dir, '.temp'))
    for filename, base_url in file_map:
        with open(os.path.join(local_dir, filename), 'rb') as local_file:
            local_data = local_file.read()
            local_hash = hashlib.sha256(local_data).hexdigest()

        res = requests.get(f'{base_url}/{filename}')
        remote_hash = hashlib.sha256(res.raw).hexdigest()
        print(f'{filename} has {"not" if remote_hash == local_hash else ""} changed')


if __name__ == '__main__':
    # TODO implement command-line args to specify file-URL pairs
    main()
