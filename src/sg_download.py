import requests
from requests.exceptions import HTTPError
from bs4 import BeautifulSoup
import json
import re
import ffmpeg
import logging
import urllib.parse
import datetime
import pathlib
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(f"sg_download_{datetime.datetime.now().strftime('%d-%b-%Y-%H-%M-%S')}.log"),
        logging.StreamHandler(sys.stdout)
    ]
)


BASE_URL = "https://sample-genie.com"
AJAX_URL = f'{BASE_URL}/wp-admin/admin-ajax.php'


def login(session, username, password):
    logging.info(f'Logging into site with user name: {username}')
    login_headers = {
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'en-US,en;q=0.9',
        'content-length': '211',
        'content-type':'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': 'https://sample-genie.com',
        'referer': 'https://sample-genie.com/',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest' 
    }

    login_data = {
        'action': {'pp_ajax_login'},
        'data': f'login_username={urllib.parse.quote(username)}&login_password={password}&login_form_id=1&pp_current_url=https%3A%2F%2Fsample-genie.com%2F&login_referrer_page='
    }
    login_resp = session.post(url=AJAX_URL, headers=login_headers, data=login_data, allow_redirects=True)
    try:
        login_resp.raise_for_status()
        logging.info("Login successful")
    except HTTPError as e:
        logging.error("Login failed")
        logging.exception(msg="HTTPError for last response.", exec_info=e)


def parse_iframe(iframe_src, session):
    logging.info("Parsing iframe src")
    soup = BeautifulSoup(iframe_src, "html.parser")
    src_url = soup.iframe.attrs["src"]

    logging.info(f"iFrame src is: {src_url}")
    logging.info("Get src url")
    vimeo_resp = session.get(f'https:{soup.iframe.attrs["src"]}')
    try:
        vimeo_resp.raise_for_status()
        logging.info("Success")
    except HTTPError as e:
        logging.error("Failed")
        logging.exception(msg="HTTPError for last response.", exec_info=e)
        return

    logging.info("Parsing iframe response for script tags")
    iframe_soup = BeautifulSoup(vimeo_resp.content, features="html.parser")
    script_tag = iframe_soup.find_all("script")

    if len(script_tag) >= 3:
        logging.info("Script tags parsed and expected number of tags found")
        logging.info("Search tags for cdn_url regex")
        result = re.search(r'({"cdn_url".*?});', script_tag[2].string)
        if len(result) >= 2:
            logging.info("Expected length of search groups returned")
            json_parsed = json.loads(result[1])
            try:
                logging.info("Parsing for stream id of highest video quality")
                streams = json_parsed['request']['files']['dash']['streams']
                for stream in streams:
                    if stream['quality'] == '1080p':
                        id_id = stream['id']
                    # elif stream['quality'] == 
                logging.info("Parse stream url")
                stream_url = json_parsed['request']['files']['dash']['cdns']['akfire_interconnect_quic']['url']
                logging.info(f"Stream url is: {stream_url}")
                logging.info("Parse video title")
                video_title = json_parsed['video']['title']
                logging.info(f"Video title is: {video_title}")
                logging.info("Parse stream url for base url")
                base_url_search_group = re.search(r'(^https:.*/)sep', stream_url)
                if len(base_url_search_group) >= 2:
                    logging.info("Parsed base url from stream url")
                    base_url = base_url_search_group[1]
                    logging.info("Create video url")
                    video_url = f'{base_url}parcel/video/{id_id.split("-")[0]}.mp4'
                    logging.debug(f"Video url: {video_url}")
                    logging.info("Crate audio url")
                    audio_id_search_group = re.search(r'audio/(.*?),', stream_url)
                    if len(audio_id_search_group) >= 2:
                        logging.info("Found expected search groups for url")
                        audio_url = f'{base_url}parcel/audio/{audio_id_search_group[1]}.mp4'
                        logging.debug(f"Audio url: {audio_url}")
                        return video_url, audio_url, video_title
                    else:
                        logging.error(f"Unable to create audio url, audio search group len is: {len(audio_id_search_group)}, expected >= 2")
                        logging.debug(f'audio_id_search_group: {audio_id_search_group}')
                else:
                    logging.error(f"Unable to parse base url from stream url: {stream_url}")
            except KeyError as e:
                logging.exception(f'Key not found:', exc_info=e)
        else:
            logging.error(f"Expected 2 or greater search groups but found: {len(result)}")
    else:
        logging.error(f"Expected 3 or greater script tags but received: {len(script_tag)}")

def setup_vpn():
    # may not be needed if not shunned from scraping
    pass

def download_file(video_url, audio_url, video_title, download_path, session):
    video_resp = session.get(video_url, stream=True)
    audio_resp = session.get(audio_url, stream=True)
    try:
        video_resp.raise_for_status()
        audio_resp.raise_for_status()
    except HTTPError as e:
        logging.error("Failed to get audio or video from url")
        logging.exception(exc_info=e)

    with open(f'{download_path}/video_{video_title}', 'w+b') as v:
        v.write(video_resp.content)
    
    with open(f'{download_path}/audio_{video_title}', 'w+b') as a:
        a.write(audio_resp.content)


def get_list_of_video_ids(session):
    logging.info("Getting list of video ids")
    # Gets initial page that will contain html to parse for all video ids and pages
    list_resp = session.get(f'{AJAX_URL}?action=search_video&s=&types%5B%5D=stream&types%5B%5D=vault', allow_redirects=True)
    soup = BeautifulSoup(list_resp.content, "html.parser")
    page_number_items = soup.find_all(class_='page-link')  # Gets class that contains list of pages
    page_numbers = [number.attrs['data-number'] for number in page_number_items]  # Extracts the page numbers
    logging.info("Scraped all page numbers for video links")
    logging.info("Start scraping for video ids by page number")
    video_ids = []
    for page in page_numbers:
        logging.info("Getting ids for page number: {page}")
        # Ajax action to return page for each page number
        page_resp = session.get(f'{AJAX_URL}?action=search_video&paged={page}&s=&types%5B%5D=stream&types%5B%5D=vault')
        soup = BeautifulSoup(page_resp.content, "html.parser")
        video_links = soup.find_all(class_='video-links panel-button alt')  # Gets class that contains video links
        video_ids += [vid.attrs['data-id'] for vid in video_links]  # Scrape ids from items
        logging.info("Finished scraping video ids for page")
    logging.info("Finished getting list of all video ids")
    logging.info(f"IDs are: {video_ids}")
    return video_ids

def get_iframe_of_video(session, video_id=None):
    if video_id:
        get_resp = session.get(f'{AJAX_URL}?action=get_video&id={video_id}', allow_redirects=True)
    else:
        get_resp = session.get(f'{AJAX_URL}?action=get_video&id=', allow_redirects=True)
    
    try:
        get_resp.raise_for_status()
        return get_resp.content
    except HTTPError as e:
        logging.error("Failed to get iframe of video")
        logging.exception(msg="HTTPError for last response.", exec_info=e)

def update_headers(session):
    video_headers = {
        'authority': 'sample-genie.com',
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'referer': 'https://sample-genie.com/',
        'sec-ch-ua': '"Not?A_Brand";v="8", "Chromium";v="108", "Google Chrome";v="108"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
        'x-requested-with': 'XMLHttpRequest'
    }
    session.headers.update(video_headers)

def main(args):
    args = parse_args(args)
    s = requests.Session()
    login(s, username=args['username'], password=args['password'])
    update_headers(s)
    video_ids = get_list_of_video_ids(s)
    if args['-n'] or args['--number_to_download']:
        video_ids = video_ids[0:args['-n']]
    for vid in video_ids:
        iframe_resp = get_iframe_of_video(vid)
        video_url, audio_url, video_title = parse_iframe(iframe_resp, s)
        if video_url and audio_url and video_title:
            video_title = video_title.replace(" - ", "_").replace(" [", "_").replace("]", "").replace(" ", "_").lower()
            download_path = f"{args['path']}{video_title}/"
            download_file(video_url, audio_url, video_title, download_path, s)

def parse_args(args):
    import argparse
    parser = argparse.ArgumentParser(description="Scrape Video and Audio from sample-genie.com")
    parser.add_argument("username", help="username")
    parser.add_argument("password", help="password for username")
    parser.add_argument("path", type=pathlib.Path, help="Path to download content", default="./")
    parser.add_argument("-f", "--force", type=bool, help="Force redownloading all content", action="store_true", default=False)
    parser.add_argument("-c", "--combine", type=bool, help="Combine audio and video into one file", action="store_true", default=False)
    parser.add_argument("-n", "--number_to_download", type=int, help="Total number of videos to download")
    return parser.parse_args(args)

if __name__ == '__main__':
    main(sys.argv[1:])
