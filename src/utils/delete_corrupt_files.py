import aiofiles
import aiofiles.os
import asyncio
from pathlib import Path
import re

async def main():
    async with aiofiles.open(str((Path(f'{__file__}') / '../test.log').resolve()), mode='r') as f:
        async for line in f:
            search_group = re.search(r'(^/workspaces.*.mp4)', line)
            if hasattr(search_group, 'groups'):
                file_name = search_group.groups()[0]
                if await aiofiles.os.path.exists(file_name):
                    await aiofiles.os.remove(file_name)
                    print(f'{file_name} deleted')
    #     contents = await f.read()
    
    # print(contents)

asyncio.run(main())