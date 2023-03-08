from polog import log, config, file_writer
import datetime
from pathlib import Path
import aiohttp
import asyncio
from asyncio import create_task, gather
import urllib
import sys
from bs4 import BeautifulSoup
from vimeo import Vimeo

# config.add_handlers(file_writer(f"{path}/sg_download_{datetime.datetime.now().strftime('%d-%b-%Y-%H-%M-%S')}.log"))
config.add_handlers(file_writer())
config.set(pool_size=1)

BASE_URL = "https://sample-genie.com"
AJAX_URL = f'{BASE_URL}/wp-admin/admin-ajax.php'

@log
async def login(session, username, password):
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
    async with session.post(url=AJAX_URL, headers=login_headers, data=login_data, allow_redirects=True) as resp:
        if resp.status != 200:
            raise Exception('Failed to login')

@log
async def update_headers(session):
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

@log
async def fetch_page(session, page):
    log(f"Getting ids for page number: {page}")
    # Ajax action to return page for each page number
    url = f'{AJAX_URL}?action=search_video&paged={page}&s=&types%5B%5D=stream&types%5B%5D=vault'
    async with session.get(url) as page_resp: 
        return await parse_page(await page_resp.read())

@log
async def parse_page(content):
    soup = BeautifulSoup(content, "html.parser")
    video_links = soup.find_all(class_='video-links panel-button alt')  # Gets class that contains video links
    video_ids = [vid.attrs['data-id'] for vid in video_links]  # Scrape ids from items
    purchased_video_links = soup.find_all(class_='video-links panel-button alt purchased')
    video_ids += [vid.attrs['data-id'] for vid in purchased_video_links]
    return video_ids


@log
async def get_list_of_video_ids(session, start_page, end_page=None, number_to_download=None):
    log("Getting list of video ids")
    # Gets initial page that will contain html to parse for all video ids and pages
    async with session.get(f'{AJAX_URL}?action=search_video&s=&types%5B%5D=stream&types%5B%5D=vault', allow_redirects=True) as resp:
        # list_resp = await resp.text()
        soup = BeautifulSoup(await resp.read(), "html.parser")
    page_number_items = soup.find_all(class_='page-link')  # Gets class that contains list of pages

    end_page = end_page - 1 if end_page else len(page_number_items)

    if number_to_download:
        page_numbers = [
            number.attrs['data-number']
            for number in page_number_items[start_page:number_to_download]
        ]
        log(f"Scraped all page numbers of {number_to_download} pages")
    else:
        page_numbers = [number.attrs['data-number'] for number in page_number_items[start_page-1:end_page]] 
        log("Scraped all page numbers for video links")
    log("Start scraping for video ids by page number")

    tasks = [create_task(fetch_page(session, page)) for page in page_numbers]
    await gather(*tasks)
    log("Finished getting list of all video ids")

    video_ids = [vid_id for task in tasks for vid_id in task.result()]
    log(f"IDs are: {video_ids}")
    log(f"Total video ids: {len(video_ids)}")
    return video_ids

@log
async def get_iframe(session, video_id):
    if video_id:
        url = f'{AJAX_URL}?action=get_video&id={video_id}'
    else:
        url = f'{AJAX_URL}?action=get_video&id='

    async with session.get(url, allow_redirects=True) as resp:
        soup = BeautifulSoup(await resp.read(), "html.parser")
        return f'https:{soup.iframe.attrs["src"]}'


@log
async def main(args):
    args = parse_args(args)
    async with aiohttp.ClientSession() as s:
        await login(s, args.username, args.password)
        await update_headers(s)
        video_ids = await get_list_of_video_ids(s, args.start_page, args.end_page, args.number_of_pages_to_download)
        vid_id_total_count = len(video_ids)
        iframe_tasks = [create_task(get_iframe(s, video_id)) for video_id in video_ids]
        await gather(*iframe_tasks)
        vimeo_urls = [create_task(Vimeo(url.result(), s).get_urls_and_title()) for url in iframe_tasks]
        await gather(*vimeo_urls)
        
        print(video_ids)


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
    asyncio.run(main(sys.argv[1:]))

# async def async_check_integrity(queue: asyncio.Queue()):
#     while True:
#         file = await queue.get()

#         try:
#             cmd = (
#                 ffmpeg
#                 .input(str(file))
#                 .output("pipe:", format="null")
#                 .global_args("-xerror")
#                 .run(capture_stdout=True, capture_stderr=True)
#             )
#             proc = await asyncio.create_subprocess_exec(*cmd)
            
#             ret = await proc.wait()

#             if ret != 0:
#                 logging.error(msg=f"{file} failed integrity check error is:")
#                 return False
#             return True
#         except ffmpeg.Error as e:        
#             logging.error(msg=f"{file} failed integrity check error is: {e.stderr}")
#             return False
