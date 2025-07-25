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
        self._base_cdn_url = None

    @classmethod
    def parse(cls, vimeo_url, session):
        cls(vimeo_url, session)._parse()
        return cls
    
    def _parse(self):
        self._get_vimeo_url()
        self._get_window_player_config()
        self._set_attributes()
        self._get_audio_url()

    def get_urls_and_title(self):
        if not self.video_url or not self.audio_url or not self.video_title:
            self._parse()
        return self.video_url, self.audio_url, self.video_title

    def _get_window_player_config(self):
        logging.info("Searching for script tags")
        soup = BeautifulSoup(self.content, "html.parser")
        script_tag = soup.find_all("script")
        if len(script_tag) > 0:
            logging.info("Script tags found and parsed")
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
        logging.info("Setting video_quality_profiles attribute")
        streams = self._window_player_config['request']['files']['dash']['streams']
        self.video_quality_profiles = {item['quality'].lower(): item['id'] for item in streams}
        logging.info("Finished setting video_quality_profiles attribute")
        logging.debug(f"{self.video_quality_profiles}")
        
        logging.info("Setting highest_video_quality attribute")
        self._get_highest_quality_id()
        logging.debug(f"highest_video_quality profile id is {self._highest_video_quality}")

        logging.info('Setting video_title attribute')
        self.video_title = self._window_player_config['video']['title']
        logging.debug(f'video_title attribute set to: {self.video_title}')
        default_cdn = self._window_player_config['request']['files']['dash']['default_cdn']
        self._cdn_stream_url = self._window_player_config['request']['files']['dash']['cdns'][default_cdn]['url']
        if base_url_search_group := re.search(
            r'(^https:.*/)sep', self._cdn_stream_url
        ):
            self._base_cdn_url = base_url_search_group[1]
        self.video_url = f'{self._base_cdn_url}parcel/video/{self._highest_video_quality.split("-")[0]}.mp4'

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
            self.audio_url = f'{self._base_cdn_url}parcel/audio/{best_bitrate_id[0].get("id")}.mp4'
            logging.info(f"Audio url: {self.audio_url}")
        except HTTPError:
            logging.exception(f"Failed to get url {self.url}", exc_info=True)

    def _get_vimeo_url(self):
        try:
            logging.info(f"Get {self.url}")
            resp = self.session.get(self.url)
            resp.raise_for_status()
            logging.info(f"Response from {self.url}, was successful")
            logging.debug(f'{resp.text}')
            self.content = resp.text
        except HTTPError:
            logging.exception(f"Failed to get url {self.url}", exc_info=True)

    def _get_highest_quality_id(self):
        logging.info("Searching for highest video quality")
        for resolution in self._video_resolutions:
            self._highest_video_quality = self.video_quality_profiles.get(resolution, None)
            if self._highest_video_quality:
                logging.info("Set highest_video_quality")
                logging.info(f"{self._highest_video_quality}")
                return
        logging.info("Failed to find highest quality video")
        logging.debug(f"{self.video_quality_profiles}")
    
