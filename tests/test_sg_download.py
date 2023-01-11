from src import sg_download
from pathlib import Path


def test_argument_parsing():
    args = ["test_user", "test_user_pass"]
    parsed_args = sg_download.parse_args(args)
    assert parsed_args.username == "test_user"
    assert parsed_args.password == "test_user_pass"
    assert parsed_args.path == Path("./")
    assert parsed_args.force == False
    assert parsed_args.combine == False
    assert parsed_args.number_to_download == None

    args = ["test_user", "test_user_pass", "-p", "/root/path", "-f", "-c", "-n", "10"]
    parsed_args = sg_download.parse_args(args)
    assert parsed_args.username == "test_user"
    assert parsed_args.password == "test_user_pass"
    assert parsed_args.path == Path("/root/path")
    assert parsed_args.force == True
    assert parsed_args.combine == True
    assert parsed_args.number_to_download == 10
