from src import sg_download
from src.sg_download import AJAX_URL
from pathlib import Path
import pytest
import requests
import requests_mock
import ffmpeg
import filecmp


@pytest.fixture(name="data_fixture_files")
def fixture_data_fixture_files(request):
    data_fixture = Path(__file__) / "../data_fixtures/sample_genie/" / request.param 
    data_fixture = data_fixture.resolve()
    files = data_fixture.iterdir()
    audio = None
    video = None
    expected = None
    for file in files:
        if file.name.startswith('audio'):
            audio = file
            continue
        elif file.name.startswith('video'):
            video = file
            continue
        else:
            expected = file

    return audio, video, expected

@pytest.fixture(name="data_fixture_content")
def fixture_data_fixture_content(request):
    data_fixture = (Path(__file__) / "../data_fixtures/sample_genie" / request.param).resolve()
    yield data_fixture.read_bytes()    

def test_argument_parsing():
    args = ["test_user", "test_user_pass"]
    parsed_args = sg_download.parse_args(args)
    assert parsed_args.username == "test_user"
    assert parsed_args.password == "test_user_pass"
    assert parsed_args.path == Path("./")
    assert parsed_args.force is False
    assert parsed_args.combine is False
    assert parsed_args.number_of_pages_to_download is None
    assert parsed_args.start_page == 1
    assert parsed_args.end_page is None
    assert parsed_args.check_integrity is True

    args = ["test_user", "test_user_pass", "-p", "/root/path", "-f", "-c", "-n", "10"]
    parsed_args = sg_download.parse_args(args)
    assert parsed_args.username == "test_user"
    assert parsed_args.password == "test_user_pass"
    assert parsed_args.path == Path("/root/path")
    assert parsed_args.force == True
    assert parsed_args.combine == True
    assert parsed_args.number_of_pages_to_download == 10
    assert parsed_args.start_page == 1
    assert parsed_args.end_page is None
    assert parsed_args.check_integrity is True

@pytest.mark.parametrize("data_fixture_files", [("integrity")], indirect=["data_fixture_files"])
def test_check_integrity(data_fixture_files):
    audio, video, _ = data_fixture_files
    assert sg_download.check_integrity(audio) is True
    assert sg_download.check_integrity(video) is False


@pytest.mark.parametrize("data_fixture_files", [("combine/rillium_bonus_prelude_making_bass")], indirect=["data_fixture_files"])
def test_combine(data_fixture_files, tmp_path):
    audio, video, expected = data_fixture_files
    d = tmp_path / video.name.lstrip('video_').rstrip('.mp4')
    d.mkdir()
    tmp_audio_file = d / audio.name
    tmp_video_file = d / video.name
    tmp_audio_file.write_bytes(audio.read_bytes())  # Copy to temp path/file
    tmp_video_file.write_bytes(video.read_bytes())
    assert filecmp.cmp(audio, tmp_audio_file)  # Make sure source matches copy
    assert filecmp.cmp(video, tmp_video_file)  
    
    sg_download.combine(d)

    combined_file = d / video.name.lstrip('video_')  # File created should be same name without video_ prefix
    assert filecmp.cmp(combined_file, expected)


@pytest.mark.parametrize("data_fixture_content,expected_result", [("get_video_ajax_resp.html", "//player.vimeo.com/video/785024886")], indirect=["data_fixture_content"])
def test_get_url_from_iframe(data_fixture_content, expected_result):
    s = requests.Session()
    with requests_mock.Mocker(session=s) as m:
        m.get(f'{AJAX_URL}?action=get_video&id=', content=data_fixture_content)
        resp = sg_download.get_url_from_iframe(s)
        assert resp == expected_result


def test_get_list_of_video_ids():
    pytest.xfail("Write Test")


@pytest.mark.parametrize(
    "data_fixture_content",
    [
        ("vimeo_audio_resp.binary"),
        ("vimeo_video_resp.binary")
    ],
    indirect=["data_fixture_content"])
def test_download_file(data_fixture_content, tmp_path):
    s = requests.Session()
    url = 'http://get_file'
    expected_file_content = data_fixture_content
    path = tmp_path / "test_file.mp4"
    with requests_mock.Mocker(session=s) as m:
        m.get(url, content=expected_file_content)
        sg_download.download_file(s, url, path, integrity_check=False)
    
    assert path.read_bytes() == expected_file_content



def test_download_files():
    pytest.xfail("Write Test")