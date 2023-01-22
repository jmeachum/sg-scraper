import sg_download
from pathlib import Path
import logging

p = Path('/workspaces/sg-scraper/downloads/videos')
total_dirs = sum(1 for _ in p.iterdir())
for running_count, directory in enumerate(p.iterdir(), start=1):
    print(f"Processing directory {running_count} of {total_dirs}")
    for file in directory.iterdir():
        print(f'Checking file: {file}')
        # TODO: potentially add a file to path to identify which files have already passed checks so the process
        # is idempotent
        if not sg_download.check_integrity(file):
            # TODO: Delete file and log
            print(f"{file} failed integrity check")