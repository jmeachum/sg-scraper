import requests
import requests_mock
from src.vimeo import Vimeo
import pytest
from pathlib import Path
import json

@pytest.fixture(name="vimeo")
def fixture_vimeo(request):
    yield Vimeo(vimeo_url=request.param, session=requests.Session())

@pytest.fixture(name="data_fixture_content")
def fixture_data_fixture_content(request):
    data_fixture = Path(__file__) / "../data_fixtures/vimeo/" / request.param 
    data_fixture = data_fixture.resolve()
    with data_fixture.open() as f:
        content = f.read()
        yield content.replace('\n', '')

@pytest.mark.parametrize("vimeo,data_fixture_content", [('http://player.vimeo.com/video/video_id', 'vimeo_no_audio_in_url_resp.html')], indirect=['vimeo','data_fixture_content'])
def test_get_url(vimeo, data_fixture_content):
    with requests_mock.Mocker(session=vimeo.session) as m:
        m.get(url=vimeo.url, text=data_fixture_content)
        vimeo.get_url()
        assert vimeo.content == data_fixture_content

@pytest.mark.parametrize("vimeo,data_fixture_content", [('http://player.vimeo.com/video/video_id', 'vimeo_no_audio_in_url_parsed_cdn_url.json')], indirect=['vimeo','data_fixture_content'])
def test_set_attributes(vimeo, data_fixture_content):
    json_data_fixture_content = json.loads(data_fixture_content)
    vimeo._window_player_config = json_data_fixture_content
    vimeo._highest_video_quality = "9e063f5a-6814-4734-adb2-2bdad787a1a8"
    
    vimeo._set_attributes()
    assert vimeo.video_quality_profiles == {"360p": "97fe0726-4ace-453e-a4cc-667f1a76de44", "540p": "b26531d4-5361-435d-8ec7-0b7b7e2440fc", "240p": "0f002591-d9d5-4e0a-a6ae-489a8b3ee1cd", "720p": "7a27ec5a-72be-4388-a164-bd17d0bb1480", "1080p": "25de01d1-4740-44ee-b512-9f33d9a28d8c", "1440p": "9e063f5a-6814-4734-adb2-2bdad787a1a8"}
    assert vimeo.video_title == json_data_fixture_content['video']['title']
    assert vimeo._cdn_stream_url == json_data_fixture_content['request']['files']['dash']['cdns']['akfire_interconnect_quic']['url']
    assert vimeo.base_url == 'https://43vod-adaptive.akamaized.net/exp=1673311840~acl=%2F0ed83b8d-57c2-411e-a172-86923b7d2b9a%2F%2A~hmac=321800014143d8d2665a30b5670dfd9089b3d0ac35802ca5a5a19f4239f20736/0ed83b8d-57c2-411e-a172-86923b7d2b9a/'
    assert vimeo.video_url == "https://43vod-adaptive.akamaized.net/exp=1673311840~acl=%2F0ed83b8d-57c2-411e-a172-86923b7d2b9a%2F%2A~hmac=321800014143d8d2665a30b5670dfd9089b3d0ac35802ca5a5a19f4239f20736/0ed83b8d-57c2-411e-a172-86923b7d2b9a/parcel/video/9e063f5a.mp4"

@pytest.mark.parametrize(
    "vimeo,quality_dict,expected_result", [
        ('http://player.vimeo.com/video/video_id', {"4320p": "4320p_id"}, '4320p_id'),
        ('http://player.vimeo.com/video/video_id', {"2160p": "2160p_id"}, '2160p_id'),
        ('http://player.vimeo.com/video/video_id', {"1440p": "1440p_id"}, '1440p_id'),
        ('http://player.vimeo.com/video/video_id', {"1080p": "1080p_id"}, '1080p_id'),
        ('http://player.vimeo.com/video/video_id', {"720p": "720p_id"}, '720p_id'),
        ('http://player.vimeo.com/video/video_id', {"360p": "360p_id", "1080p": "1080p_id"}, '1080p_id'),
        ('http://player.vimeo.com/video/video_id', {"240p": "240p_id", "360p": "360p_id", "1080p": "1080p_id", "1440p": "1440p_id"}, '1440p_id')
        ], indirect=['vimeo'])
def test_get_highest_resolution(vimeo, quality_dict, expected_result):
    vimeo.video_quality_profiles = quality_dict
    vimeo._get_highest_quality_id()
    assert vimeo._highest_video_quality == expected_result

@pytest.mark.parametrize(
    "vimeo,script_tag,expected_result", [
        ('http://player.vimeo.com/video/video_id', '<script> window.playerConfig = {"cdn_url": "https://f.vimeocdn.com" }; var=other_javascript_text </script>', json.loads('{"cdn_url": "https://f.vimeocdn.com" }')),
        ('http://player.vimeo.com/video/video_id', '<script> window.playerConfig = { "cdn_url": "https://f.vimeocdn.com" }; var=other_javascript_text </script>', json.loads('{"cdn_url": "https://f.vimeocdn.com" }')),
        ('http://player.vimeo.com/video/video_id', '<script> window.playerConfig = {   "cdn_url": "https://f.vimeocdn.com" }; var=other_javascript_text </script>', json.loads('{"cdn_url": "https://f.vimeocdn.com" }'))
    ],
    indirect=["vimeo"])
def test_get_window_player_config(vimeo, script_tag, expected_result):
    vimeo.content = script_tag
    vimeo._get_window_player_config()
    assert vimeo._window_player_config == expected_result

@pytest.mark.parametrize(
    "vimeo,data_fixture_content,expected_result", [
        ('http://player.vimeo.com/video/video_id', 'vimeo_no_audio_in_url_master.json', "https://43vod-adaptive.akamaized.net/exp=1673311840~acl=%2F0ed83b8d-57c2-411e-a172-86923b7d2b9a%2F%2A~hmac=321800014143d8d2665a30b5670dfd9089b3d0ac35802ca5a5a19f4239f20736/0ed83b8d-57c2-411e-a172-86923b7d2b9a/parcel/audio/b26531d4.mp4")
    ],
    indirect=["vimeo", "data_fixture_content"]
)
def test_get_audio_url(vimeo, data_fixture_content, expected_result):
    vimeo._cdn_stream_url = "https://stream_url"
    vimeo.base_url = "https://43vod-adaptive.akamaized.net/exp=1673311840~acl=%2F0ed83b8d-57c2-411e-a172-86923b7d2b9a%2F%2A~hmac=321800014143d8d2665a30b5670dfd9089b3d0ac35802ca5a5a19f4239f20736/0ed83b8d-57c2-411e-a172-86923b7d2b9a/"
    with requests_mock.Mocker(session=vimeo.session) as m:
        m.get(vimeo._cdn_stream_url, text=data_fixture_content)
        vimeo._get_audio_url()
        
    assert vimeo.audio_url == expected_result
