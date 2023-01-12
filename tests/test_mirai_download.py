from src import mirai_download
from pathlib import Path
import requests
import requests_mock
import pytest
import json

@pytest.fixture(name="data_fixture_content")
def fixture_data_fixture_content(request):
    data_fixture = Path(__file__) / "../data_fixtures/mirai" / request.param 
    data_fixture = data_fixture.resolve()
    with data_fixture.open() as f:
        content = f.read()
        yield content.replace('\n', '')

def test_login():
    s = requests.Session()
    mirai_download.login(session=s, username="", password="")

@pytest.mark.parametrize("data_fixture_content", [("get_all_videos.html")], indirect=["data_fixture_content"])
def test_get_video_urls(data_fixture_content):
    url = 'https://live.bonsaimirai.com/library/videos_all'
    s = requests.Session()
    expected_return = Path(__file__) / "../data_fixtures/mirai/get_all_video_urls_expected_return.json"
    expected_return = expected_return.resolve()
    expected_return = json.load(expected_return.open())
    with requests_mock.Mocker(session=s) as m:
        m.get(url, text=data_fixture_content)
        url_list = mirai_download.get_video_urls(s)
        assert url_list == expected_return

@pytest.mark.parametrize("data_fixture_content", [("get_video_url_resp.html")], indirect=["data_fixture_content"])
def test_get_video_urls(data_fixture_content):
    url = "https://live.bonsaimirai.com/library/video/bristlecone-design-naturalization"
    s = requests.Session()
    with requests_mock.Mocker(session=s) as m:
        m.get(url, text=data_fixture_content)
        vimeo_url = mirai_download.get_vimeo_url(s, url)
        assert vimeo_url == "https://player.vimeo.com/video/786077889"