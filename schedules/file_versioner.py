import hashlib
import json
import logging
import os
import sys
from typing import Dict

import requests
from bs4 import BeautifulSoup


def find_known_schedules(timeout: int = 10) -> Dict:
    """
    Get the URLs of all known schedules from the Stevens website.
    :param timeout: The timeout for the initial HTTP requests
    :note: Must navigate Stevens' website as a normal user would to find up-to-date URLS (cannot hardcode),
    since if a file changes but the old one is deleted then the hash of stevens.edu/old_schedule.jpg
    will still equal the local copy, even though the website now directs users to stevens.edu/new_schedule.png
    """
    red_gray_sat_sun_url = 'https://www.stevens.edu/campus-life/life-hoboken/transportation/stevens-shuttles/stevens-shuttle-red-gray-line-schedule'
    blue_url = 'https://www.stevens.edu/campus-life/life-hoboken/transportation/stevens-shuttles/stevens-shuttle-blue-line-schedule'
    green_url = 'https://www.stevens.edu/campus-life/life-hoboken/transportation/stevens-shuttles/stevens-green-line-shuttle-schedule'

    # TODO Make this function generic where possible
    # This was written explicitly at first in order to determine which schedules were "special cases" (many were)
    requests_exceptions = (requests.exceptions.Timeout, requests.exceptions.ConnectionError,
                           requests.exceptions.HTTPError, requests.exceptions.TooManyRedirects)

    red_gray_soup, blue_soup,  green_soup = None, None, None
    try:
        red_gray_resp = requests.get(red_gray_sat_sun_url, timeout=timeout)
        red_gray_resp.raise_for_status()
        red_gray_soup = BeautifulSoup(red_gray_resp.text, 'html5lib')
    except requests_exceptions:
        logging.error('Unable to connect to red/gray schedule URL. Will not be able to check these for updates')
    try:
        blue_resp = requests.get(blue_url, timeout=timeout)
        blue_resp.raise_for_status()
        blue_soup = BeautifulSoup(blue_resp.text, 'html5lib')
    except requests_exceptions:
        logging.error('Unable to connect to blue schedule URL. Will not be able to check for updates')
    try:
        green_resp = requests.get(green_url, timeout=timeout)
        green_resp.raise_for_status()
        green_soup = BeautifulSoup(green_resp.text, 'html5lib')
    except requests_exceptions:
        logging.error('Unable to connect to green schedule URL. Will not be able to check for updates')

    red_btns = red_gray_soup.find_all(attrs={'class': 'link_button_sm background_red'})
    gray_btns = red_gray_soup.find_all(attrs={'class': 'link_button_sm background_gray'})
    blue_parent_class = blue_soup.find(attrs={'class': 'field-item even', 'property': 'content:encoded'})
    green_parent_class = green_soup.find(attrs={'class': 'field-item even', 'property': 'content:encoded'})

    results = {'red_morning.csv': None, 'red_weekday.csv': None, 'red_saturday.csv': None, 'red_sunday.csv': None,
               'gray_weekday.csv': None, 'gray_night.csv': None,
               'green_weekday.csv': None,
               'blue_weekday.csv': None}
    if not red_btns:
        logging.error('Could not find any red line buttons. Will not be able to check for updates')
    else:
        for btn in red_btns:
            btn_text = btn.text.strip().upper()
            if btn_text == 'EARLY MORNING SHUTTLE':
                try:
                    results['red_morning.csv'] = btn.parent['href']
                except KeyError:
                    logging.error('Unable to locate red line morning URL. Will not be able to check for updates')
            elif btn_text == 'RED LINE SHUTTLE':
                try:
                    results['red_weekday.csv'] = btn.parent['href']
                except KeyError:
                    logging.error('Unable to locate red line weekday URL. Will not be able to check for updates')
            elif btn_text == 'SATURDAY':
                try:
                    results['red_saturday.csv'] = btn['href']
                except KeyError:
                    logging.error('Unable to locate red line saturday URL. Will not be able to check for updates')
            elif btn_text == 'SUNDAY':
                try:
                    a_elem = btn.children.__next__()
                    assert a_elem.name.lower() == 'a'
                    results['red_sunday.csv'] = a_elem['href']
                except (KeyError, AttributeError, AssertionError):
                    logging.error('Unable to locate red line sunday URL. Will not be able to check for updates')
    if not gray_btns:
        logging.error('Could not find any gray line buttons. Will not be able to check for updates')
    else:
        for btn in gray_btns:
            btn_text = btn.text.strip().upper()
            if btn_text == 'GRAY LINE SHUTTLE':
                try:
                    results['gray_weekday.csv'] = btn.parent['href']
                except KeyError:
                    logging.error('Unable to locate gray line weekday URL. Will not be able to check for updates')
            elif btn_text == 'LATE NIGHT SHUTTLE':
                try:
                    results['gray_night.csv'] = btn.parent['href']
                except KeyError:
                    logging.error('Unable to locate gray line weekday URL. Will not be able to check for updates')
    if blue_parent_class is None:
        logging.error('Could not find blue line image container. Will not be able to check for updates')
    else:
        try:
            children = list(blue_parent_class.children)
            h2_elem, p_elem = children[0], children[2]
            assert h2_elem.text.strip().upper() == 'STEVENS SHUTTLE BLUE LINE SCHEDULE'
            img_elem = p_elem.children.__next__()
            assert img_elem.name.lower() == 'img'
            results['blue_weekday.csv'] = img_elem['src']
        except (KeyError, AttributeError, AssertionError):
            logging.error('Could not locate blue line URL. Will not be able to check for updates')
    if green_parent_class is None:
        logging.error('Could not find green line image container. Will not be able to check for updates')
    else:
        try:
            children = list(green_parent_class.children)
            h2_elem, p_elem = children[0], children[2]
            assert h2_elem.text.strip().upper() == 'STEVENS GREEN LINE SHUTTLE SCHEDULE'
            img_elem = p_elem.children.__next__()
            assert img_elem.name.lower() == 'img'
            results['green_weekday.csv'] = img_elem['src']
        except (KeyError, AttributeError, AssertionError):
            logging.error('Could not locate green line URL. Will not be able to check for updates')

    for filename, url in results.items():
        if url and url[:4].lower() != 'http':
            results[filename] = f'https://www.stevens.edu{url}'
    return results


def main():
    urls_by_schedule = find_known_schedules()
    needs_update = {filename: True for filename in urls_by_schedule.keys()}
    local_dir = os.path.join('originals', 'spring18')

    with open(os.path.join('generated', 'file_info.json'), 'r') as info_file:
        local_file_info = json.load(info_file)['file_info']

    for filename, url in urls_by_schedule.items():
        try:
            with open(os.path.join(local_dir, local_file_info[filename]['original_name']), 'rb') as local_file:
                local_data = local_file.read()
                local_hash = hashlib.sha256(local_data).hexdigest()
        except FileNotFoundError:
            logging.error(f'No local file for {filename}')
            continue
        res = requests.get(url)
        remote_hash = hashlib.sha256(res.content).hexdigest()
        if remote_hash == local_hash:
            needs_update[filename] = False
    print(json.dumps(needs_update, indent=2))


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(levelname)s:%(message)s')
    main()
