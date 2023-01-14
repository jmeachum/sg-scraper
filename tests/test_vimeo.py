import requests
import requests_mock
from src.vimeo import Vimeo
import pytest
from pathlib import Path
import json
import yaml

@pytest.fixture(name="vimeo")
def fixture_vimeo(request):
    if hasattr(request, 'param'):
        yield Vimeo(vimeo_url=request.param, session=requests.Session())
    else:
        yield Vimeo(vimeo_url='http://player.vimeo.com/video/video_id', session=requests.Session())

@pytest.fixture(name="data_fixture_content")
def fixture_data_fixture_content(request):
    data_fixture = Path(__file__) / "../data_fixtures/vimeo/" / request.param 
    data_fixture = data_fixture.resolve()
    with data_fixture.open() as f:
        content = f.read()
        yield content.replace('\n', '')

@pytest.fixture(name='load_expected_result')
def fixture_load_expected_result(request):
    if hasattr(request, 'param'):
        expected_result_path = Path(__file__) / "../data_fixtures/vimeo" / request.param
        expected_result_path = expected_result_path.resolve()
        with expected_result_path.open() as f:
            parsed_yaml = yaml.safe_load(f.read())      
        yield parsed_yaml


@pytest.mark.parametrize("data_fixture_content", [('no_audio_in_url/get_url_resp.html')], indirect=['data_fixture_content'])
def test_get_url(vimeo, data_fixture_content):
    with requests_mock.Mocker(session=vimeo.session) as m:
        m.get(url=vimeo.url, text=data_fixture_content)
        vimeo._get_vimeo_url()
        assert vimeo.content == data_fixture_content

@pytest.mark.parametrize(
    "data_fixture_content,load_expected_result",
    [
        ('no_audio_in_url/parsed_cdn_url.json','no_audio_in_url/expected_result/result.yml'),
        ('no_akfire_interconnect_quick_cdn/parsed_cdn_url.json','no_akfire_interconnect_quick_cdn/expected_result/result.yml')
    ],
    indirect=['data_fixture_content', 'load_expected_result'])
def test_set_attributes(vimeo, data_fixture_content, load_expected_result):
    json_data_fixture_content = json.loads(data_fixture_content)
    vimeo._window_player_config = json_data_fixture_content
    vimeo._highest_video_quality = load_expected_result.get('highest_video_quality', None)

    vimeo._set_attributes()
    assert vimeo.video_quality_profiles == load_expected_result.get('video_quality_profiles', None)
    assert vimeo.video_title == load_expected_result.get('video_title', None)
    assert vimeo._cdn_stream_url == load_expected_result.get('cdn_stream_url', None)
    assert vimeo._base_cdn_url == load_expected_result.get('base_cdn_url', None)
    assert vimeo.video_url == load_expected_result.get('video_url', None)

@pytest.mark.parametrize(
    "quality_dict,expected_result", [
        ({"4320p": "4320p_id"}, '4320p_id'),
        ({"2160p": "2160p_id"}, '2160p_id'),
        ({"1440p": "1440p_id"}, '1440p_id'),
        ({"1080p": "1080p_id"}, '1080p_id'),
        ({"720p": "720p_id"}, '720p_id'),
        ({"360p": "360p_id", "1080p": "1080p_id"}, '1080p_id'),
        ({"240p": "240p_id", "360p": "360p_id", "1080p": "1080p_id", "1440p": "1440p_id"}, '1440p_id')
        ])
def test_get_highest_resolution(vimeo, quality_dict, expected_result):
    vimeo.video_quality_profiles = quality_dict
    vimeo._get_highest_quality_id()
    assert vimeo._highest_video_quality == expected_result

@pytest.mark.parametrize(
    "script_tag,expected_result", [
        ('<script> window.playerConfig = {"cdn_url": "https://f.vimeocdn.com" }; var=other_javascript_text </script>', json.loads('{"cdn_url": "https://f.vimeocdn.com" }')),
        ('<script> window.playerConfig = { "cdn_url": "https://f.vimeocdn.com" }; var=other_javascript_text </script>', json.loads('{"cdn_url": "https://f.vimeocdn.com" }')),
        ('<script> window.playerConfig = {   "cdn_url": "https://f.vimeocdn.com" }; var=other_javascript_text </script>', json.loads('{"cdn_url": "https://f.vimeocdn.com" }'))
    ])
def test_get_window_player_config(vimeo, script_tag, expected_result):
    vimeo.content = script_tag
    vimeo._get_window_player_config()
    assert vimeo._window_player_config == expected_result

@pytest.mark.parametrize(
    "data_fixture_content,expected_result", [
        ('no_audio_in_url/master.json', "https://43vod-adaptive.akamaized.net/exp=1673311840~acl=%2F0ed83b8d-57c2-411e-a172-86923b7d2b9a%2F%2A~hmac=321800014143d8d2665a30b5670dfd9089b3d0ac35802ca5a5a19f4239f20736/0ed83b8d-57c2-411e-a172-86923b7d2b9a/parcel/audio/b26531d4.mp4")
    ],
    indirect=["data_fixture_content"])
def test_get_audio_url(vimeo, data_fixture_content, expected_result):
    vimeo._cdn_stream_url = "https://stream_url"
    vimeo._base_cdn_url = "https://43vod-adaptive.akamaized.net/exp=1673311840~acl=%2F0ed83b8d-57c2-411e-a172-86923b7d2b9a%2F%2A~hmac=321800014143d8d2665a30b5670dfd9089b3d0ac35802ca5a5a19f4239f20736/0ed83b8d-57c2-411e-a172-86923b7d2b9a/"
    with requests_mock.Mocker(session=vimeo.session) as m:
        m.get(vimeo._cdn_stream_url, text=data_fixture_content)
        vimeo._get_audio_url()
        
    assert vimeo.audio_url == expected_result
