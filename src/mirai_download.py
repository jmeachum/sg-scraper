import requests
from requests.exceptions import HTTPError
from bs4 import BeautifulSoup
import json
import re
import ffmpeg
import logging
import urllib.parse
import datetime
from pathlib import Path
import sys
from vimeo import Vimeo

BASE_URL = "https://live.bonsaimirai.com"
LOGIN_URL = f"{BASE_URL}/sign_in"

def setup_log(path):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(f"{path}/sg_download_{datetime.datetime.now().strftime('%d-%b-%Y-%H-%M-%S')}.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )

def login(session, username, password):
    logging.info(f'Logging into site with user name: {username}')
    headers = {
        'authority': 'live.bonsaimirai.com',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'accept-language': 'en-US,en;q=0.9',
        'dnt': "1",
        'pragma': 'no-cache',
        'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36'
    }

    login_headers = {
        'authority': 'live.bonsaimirai.com',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'accept-language': 'en-US,en;q=0.9',
        'cached-control': 'no-cache',
        'content-type': 'application/x-www-form-urlencoded',
        'dnt': "1",
        'origin': BASE_URL,
        'pragma': 'no-cache',
        'referer': LOGIN_URL,
        'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36'
    }


    try:
        resp = session.get(url=LOGIN_URL, headers=headers, allow_redirects=True)  # Gets cookies for session
        resp.raise_for_status()
        csrf_token = resp.cookies.get_dict().get('exp_csrf_token')
        login_data = f'ACT=9&RET={urllib.parse.quote(BASE_URL, safe="")}%2F&site_id=1&csrf_token={csrf_token}&username={urllib.parse.quote(username)}&password={password}'

        session.headers.update(login_headers)
        resp_login = session.post(url=f'{BASE_URL}', data=login_data, allow_redirects=True)
        resp_login.raise_for_status()
        logging.info("Login successful")
    except HTTPError as e:
        logging.error("Login failed")
        logging.exception(msg="HTTPError for last response.", exec_info=e)

def get_video_urls(session):
    # The video link index does not require authentication
    # https://live.bonsaimirai.com/library/videos_all
    resp = session.get("https://live.bonsaimirai.com/library/videos_all")
    # parse out just the function that has the things in it
    resp_dict = re.search(r'MIRAI_GLOBALS.VIDEOS.ENTRIES =(.*\]);', resp.text)
    resp_dict = json.loads(resp_dict.groups()[0])
    url_list = []
    for item in resp_dict:
        url_list.append({"url": item["url"], "url_title": item["url_title"]})
    return url_list

def get_vimeo_url(session, mirai_video_url):
    resp = session.get(mirai_video_url)
    soup = BeautifulSoup(resp.content, "html.parser")
    return soup.iframe.attrs["src"]

def main(args):
    args = parse_args(args)
    setup_log(args.path)
    s = requests.Session()
    login(s, username=args.username, password=args.password)

def parse_args(args):
    import argparse
    parser = argparse.ArgumentParser(description="Scrape Video and Audio from live.mirai.com")
    parser.add_argument("username", help="username")
    parser.add_argument("password", help="password for username")
    parser.add_argument("-p", "--path", type=Path, help="Path to download content", default="./")
    parser.add_argument("-f", "--force", help="Force redownloading all content", action="store_true", default=False)
    parser.add_argument("-c", "--combine", help="Combine audio and video into one file", action="store_true", default=False)
    parser.add_argument("-n", "--number_of_pages_to_download", type=int, help="Total number of video pages to download")
    return parser.parse_args(args)

if __name__ == '__main__':
    main(sys.argv[1:])