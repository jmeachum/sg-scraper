import sg_download
from pathlib import Path
import asyncio
import cProfile, pstats
from typing import Iterable
import sys
import os

### Test code 1:

# 8703 function calls (8275 primitive calls) in 123.096 seconds

# async def main():
#     p = Path('/workspaces/sg-scraper/test_async')
#     total_dirs = sum(1 for _ in p.iterdir())
#     for running_count, directory in enumerate(p.iterdir(), start=1):
#         print(f"Processing directory {running_count} of {total_dirs}")
#         for file in directory.iterdir():
#             print(f'Checking file: {file}')
#             if not await sg_download.async_check_integrity(file):
#                 print(f"{file} failed integrity check")

# profiler = cProfile.Profile()
# profiler.enable()
# asyncio.run(main())
# profiler.disable()
# stats = pstats.Stats(profiler).sort_stats('ncalls')
# stats.print_stats()

######################################################################

# Test code 2:

# 8944 function calls (8516 primitive calls) in 117.158 seconds
# async def check_integrity(file):
#     print(f'Checking file: {file}')
#     if not await sg_download.async_check_integrity(file):
#         print(f"{file} failed integrity check")

# async def print_path(path):
#     print(f"Processing {path}")
#     await asyncio.gather(*map(check_integrity, path.iterdir()))

# async def main():
#     p = Path('/workspaces/sg-scraper/test_async')
#     await asyncio.gather(*map(print_path, p.iterdir()))

# profiler = cProfile.Profile()
# profiler.enable()
# asyncio.run(main())
# profiler.disable()
# stats = pstats.Stats(profiler).sort_stats('ncalls')
# stats.print_stats()

########################################################################



# Test code 3:

async def async_check_integrity(queue: asyncio.Queue()):
    while True:
        file = await queue.get()
        print(f'Processing file: {file}')

        cmd = ["/usr/bin/ffmpeg", "-i", str(file), "-xerror", "-f", "null", "pipe:"]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
            )
        
        ret = await proc.wait()
        if ret != 0:
            print(file, "failed checks", file=sys.stderr)

        
        queue.task_done()


async def main():
    p = Path('/workspaces/sg-scraper/downloads/videos')

    Ntask = os.cpu_count()  # includes logical cores
    if not isinstance(Ntask, int):
        Ntask = 2

    queue = asyncio.Queue()
    for path in p.iterdir():
        for file in path.iterdir():
            await queue.put(file)

    tasks = [asyncio.create_task(async_check_integrity(queue)) for _ in range(Ntask)]
    await queue.join()

    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)


import datetime
start = datetime.datetime.now()
print(f"Starting at {start}")
asyncio.run(main())
end = datetime.datetime.now()
print(f'Ending at {end}')
print(f'Total time to complete: {end - start}')


