from requests.exceptions import HTTPError
import logging
from bs4 import BeautifulSoup
import re
import json


class Vimeo(object):

    def __init__(self, vimeo_url=None, session=None) -> None:
        self.url = vimeo_url
        self.session = session
        self.content = None
        self.video_quality_profiles = None
        self._video_resolutions = ["4320p", "2160p", "1440p", "1080p", "720p", "360p", "240p"]
        self._highest_video_quality = None
        self.video_title = None
        self._window_player_config = None
        self.video_url = None
        self.audio_url = None

    def parse(self):
        pass
    
    def _get_window_player_config(self):
        logging.info("Searching for script tags")
        soup = BeautifulSoup(self.content, "html.parser")
        script_tag = soup.find_all("script")
        if len(script_tag) > 0:
            logging.info("Script tags parsed")
            logging.info("Search tags for cdn_url regex")
            for tag in script_tag:
                result = re.search(r'({\s*"cdn_url".*?});', tag.string)
                if result and len(result.groups()) == 1:
                    logging.info("Found cdn_url in script tag, loading as attribute")
                    self._window_player_config = json.loads(result[1])
                    break
        else:
            logging.error("Did not find any script tags")


    def _set_attributes(self):
        logging.info("Setting video quality dictionary from source")
        streams = self._window_player_config['request']['files']['dash']['streams']
        self.video_quality_profiles = {item['quality'].lower(): item['id'] for item in streams}
        logging.debug(f"Finished building quality map: {self.video_quality_profiles}")
        logging.info('Setting video title attribute')
        self.video_title = self._window_player_config['video']['title']
        logging.debug(f'Set video title attribute to: {self.video_title}')
        self._cdn_stream_url = self._window_player_config['request']['files']['dash']['cdns']['akfire_interconnect_quic']['url']
        if base_url_search_group := re.search(
            r'(^https:.*/)sep', self._cdn_stream_url
        ):
            self.base_url = base_url_search_group[1]
        self.video_url = f'{self.base_url}parcel/video/{self._highest_video_quality.split("-")[0]}.mp4'

    def _get_audio_url(self):
        try:
            resp = self.session.get(self._cdn_stream_url)
            resp.raise_for_status()
            logging.info(f"Response from {self._cdn_stream_url}, was successful")
            logging.debug(f"{resp.text}")
            resp_json = json.loads(resp.text)
            best_sample_rate = [max(item["sample_rate"] for item in resp_json["audio"])]
            best_sample_rate = [item for item in resp_json["audio"] if item['sample_rate'] in best_sample_rate]
            best_bitrate = [max(item["bitrate"] for item in best_sample_rate)][0]
            best_bitrate_id = [item for item in best_sample_rate if item['bitrate'] == best_bitrate]
            # best_bitrate = [max(item["bitrate"] for item in resp_json["audio"])][0]
            # best_bitrate_id = [item for item in resp_json["audio"] if item['bitrate'] == best_bitrate]
            self.audio_url = f'{self.base_url}parcel/audio/{best_bitrate_id[0].get("id")}.mp4'
        except HTTPError as e:
            logging.exception(msg=f"Failed to get url {self.url}", exc_info=e)

    def get_url(self):
        try:
            logging.info(f"Get {self.url}")
            resp = self.session.get(self.url)
            resp.raise_for_status()
            logging.info(f"Response from {self.url}, was successful")
            logging.debug(f'{resp.text}')
            self.content = resp.text
        except HTTPError as e:
            logging.exception(msg=f"Failed to get url {self.url}", exc_info=e)

    def _get_highest_quality_id(self):
        for resolution in self._video_resolutions:
            self._highest_video_quality = self.video_quality_profiles.get(resolution, None)
            if self._highest_video_quality:
                break
    
