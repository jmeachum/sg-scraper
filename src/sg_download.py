import requests
from requests.exceptions import HTTPError
from bs4 import BeautifulSoup
import re
import ffmpeg
import logging
import urllib.parse
import datetime
from pathlib import Path
import sys
from vimeo import Vimeo
import time



BASE_URL = "https://sample-genie.com"
AJAX_URL = f'{BASE_URL}/wp-admin/admin-ajax.php'

def setup_log(path):
    # TODO: Create path if it does not exist
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
    
    try:
        login_resp = session.post(url=AJAX_URL, headers=login_headers, data=login_data, allow_redirects=True)
        login_resp.raise_for_status()
        logging.info("Login successful")
    except HTTPError as e:
        logging.error("Login failed")
        logging.exception("HTTPError for last response.", exec_info=True)


def setup_vpn():
    # may not be needed if not shunned from scraping
    pass

def download_files(video_url, audio_url, video_title, download_path, session, integrity_check, force_download=False):
    if not download_path.exists():
        logging.info(f"Creating {download_path} and all parents that do not exist")
        download_path.mkdir(parents=True)

    video_path = download_path / f'video_{video_title}'
    audio_path = download_path / f'audio_{video_title}'
    if not video_path.suffix or video_path.suffix != '.mp4':
        video_path = video_path.with_suffix('.mp4')
    if not audio_path.suffix or audio_path.suffix != '.mp4':
        audio_path = audio_path.with_suffix('.mp4')

    if not video_path.exists() or force_download:
        logging.info(f"Video file {video_path} does not exist, or force set to true, downloading")
        download_file(session, video_url, video_path, integrity_check)
    else:
        logging.info(f"File {video_path} exists, skipping")

    if not audio_path.exists() or force_download:
        logging.info(f"Audio file {audio_path} does not exist, or force set to true, downloading")
        download_file(session, audio_url, audio_path, integrity_check)
    else:
        logging.info(f"File {audio_path} exists, skipping")

def download_file(session, url, path, integrity_check):
    try:
        video_resp = session.get(url, stream=True)
        video_resp.raise_for_status()
        path.write_bytes(video_resp.content)
        if integrity_check and not check_integrity(path):
            # TODO: Add max recursion control handler
            download_file(session, url, path, integrity_check)
    except HTTPError as e:
        # TODO: Handle session termination and timeout exceptions
        logging.exception(f'Failed to get data from url {e}')

def get_list_of_video_ids(session, start_page, end_page=None, number_to_download=None):
    logging.info("Getting list of video ids")
    # Gets initial page that will contain html to parse for all video ids and pages
    list_resp = session.get(f'{AJAX_URL}?action=search_video&s=&types%5B%5D=stream&types%5B%5D=vault', allow_redirects=True)
    soup = BeautifulSoup(list_resp.content, "html.parser")
    page_number_items = soup.find_all(class_='page-link')  # Gets class that contains list of pages

    end_page = end_page - 1 if end_page else len(page_number_items)

    if number_to_download:
        page_numbers = [
            number.attrs['data-number']
            for number in page_number_items[start_page:number_to_download]
        ]
        logging.info(f"Scraped all page numbers of {number_to_download} pages")
    else:
        page_numbers = [number.attrs['data-number'] for number in page_number_items[start_page-1:end_page]] 
        logging.info("Scraped all page numbers for video links")
    logging.info("Start scraping for video ids by page number")
    video_ids = []
    for page in page_numbers:
        logging.info(f"Getting ids for page number: {page}")
        # Ajax action to return page for each page number
        page_resp = session.get(f'{AJAX_URL}?action=search_video&paged={page}&s=&types%5B%5D=stream&types%5B%5D=vault')
        soup = BeautifulSoup(page_resp.content, "html.parser")
        video_links = soup.find_all(class_='video-links panel-button alt')  # Gets class that contains video links
        video_ids += [vid.attrs['data-id'] for vid in video_links]  # Scrape ids from items
        purchased_video_links = soup.find_all(class_='video-links panel-button alt purchased')
        video_ids += [vid.attrs['data-id'] for vid in purchased_video_links]
        logging.info(f"Finished scraping video ids for page: {page}")
    logging.info("Finished getting list of all video ids")
    logging.info(f"IDs are: {video_ids}")
    logging.info(f"Total video ids: {len(video_ids)}")
    return video_ids


def get_url_from_iframe(session, video_id=None):
    try:
        if video_id:
            resp = session.get(f'{AJAX_URL}?action=get_video&id={video_id}', allow_redirects=True)
        else:
            resp = session.get(f'{AJAX_URL}?action=get_video&id=', allow_redirects=True)
        resp.raise_for_status()
    except HTTPError:
        logging.error("Failed to get iframe of video")
        logging.exception("HTTPError for last response.", exc_info=True)

    soup = BeautifulSoup(resp.content, "html.parser")
    return soup.iframe.attrs["src"]

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

def combine(path):
    combined_filename = path / f"{path.name}.mp4"
    if not combined_filename.exists():
        f1, f2 = path.iterdir()
        logging.info(f"Combining {f1.name} and {f2.name}")
        try:
            input_1 = ffmpeg.input(str(f1))
            input_2 = ffmpeg.input(str(f2))
            (
                ffmpeg
                .output(
                    input_1,
                    input_2,
                    str(combined_filename),
                    codec = "copy"
                    )
                .global_args("-xerror")
                .run(capture_stdout=True, capture_stderr=True)
            )
            logging.info(f"Combining {f1.name} and {f2.name} complete")
            # TODO: Maybe check integrity here, but process should fail if the process was not successful, maybe redudant
        except ffmpeg.Error as e:        
            logging.error(msg=f"Failed to combine audio and video error: {e.stderr}")


def combine_only(path):
    # Combines all video and audio in a root path, e.g. path = downloads, will look in all directories in downloads/child_paths
    # for child_path_name/video_child_path_name.mp4, child_path_name/audio_child_path_name.mp4 and create a combined audio/video file of
    # child_path_name/child_path_name.mp4 so long as it does not already exist
    pass

def get_courses():
    # First get request to /courses, returns purchased and unpurchased courses
    # purchased courses have ids, lines 622 and 635 of tests/data_fixtures/get_courses/get_courses_resp.html

    # Get request to ajax per id returns the response in tests/data_fixtures/get_courses/get_course_id_ajax_resp.html:
    # https://sample-genie.com/wp-admin/admin-ajax.php?action=get_course_videos&id=199698

    # Get request to ajax per video id returns the response in tests/data_fixtures/get_courses/get_course_video_ajax_resp.html
    # https://sample-genie.com/wp-admin/admin-ajax.php?action=get_course_video&courseID=199698&videoID=1
    pass

def check_integrity(path):
    time.sleep(1) # To give file operation time to finish writing before check
    try:
        (
            ffmpeg
            .input(str(path))
            .output("pipe:", format="null")
            .global_args("-xerror")
            .run(capture_stdout=True, capture_stderr=True)
        )
        logging.info(f"{path} passed integrity check")
        return True
    except ffmpeg.Error as e:        
        logging.error(msg=f"{path} failed integrity check error is: {e.stderr}")
        return False
   
def main(args):
    args = parse_args(args)
    setup_log(args.path)
    s = requests.Session()
    login(s, username=args.username, password=args.password)
    update_headers(s)
    video_ids = get_list_of_video_ids(s, args.start_page, args.end_page, args.number_of_pages_to_download)
    vid_id_total_count = len(video_ids)
    for processed_vid_count, vid in enumerate(video_ids, start=1):
        vimeo_url = f'https:{get_url_from_iframe(s, vid)}'
        v = Vimeo(vimeo_url, s)
        video_url, audio_url, video_title = v.get_urls_and_title()
        if video_url and audio_url and video_title:
            video_title = re.sub('[^a-zA-Z0-9_. ]', '', video_title).lower()
            video_title = re.sub(' +', '_', video_title)
            download_path = Path(f"{args.path.absolute()}/videos/{video_title}".replace(".mp4", ""))
            download_files(video_url, audio_url, video_title, download_path, s, args.check_integrity, args.force)
            if args.combine:
                combine(download_path)
        logging.info(f"Processed video {processed_vid_count} of {vid_id_total_count}")

def parse_args(args):
    # Add https://docs.python.org/3/library/argparse.html#sub-commands
    import argparse
    parser = argparse.ArgumentParser(description="Scrape Video and Audio from sample-genie.com")
    parser.add_argument("username", help="username")
    parser.add_argument("password", help="password for username")
    parser.add_argument("-p", "--path", type=Path, help="Path to download content", default="./")
    parser.add_argument("-f", "--force", help="Force redownloading all content", action="store_true")
    parser.add_argument("-c", "--combine", help="Combine audio and video into one file", action="store_true")
    parser.add_argument("-n", "--number-of-pages-to-download", type=int, help="Total number of video pages to download")
    parser.add_argument("-s", "--start-page", type=int, help="Page to start from", default=1)
    parser.add_argument("-e", "--end-page", type=int, help="Page to end on")
    parser.add_argument("-i", "--check-integrity", action="store_true", default=True)
    return parser.parse_args(args)

if __name__ == '__main__':
    main(sys.argv[1:])
