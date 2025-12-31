import zlib
import os
import mmap
import asyncio

class DirectExtractor:
    def __init__(self, client, parser):
        self.client = client
        self.parser = parser

    async def extract(self, filename, output_path):
        file_info = self.parser.files[filename]
        start_pos = await self.parser.get_data_start(filename)
        file_size = file_info['comp_size']
        
        if file_info['method'] == 8:
            await self._extract_sequential_compressed(start_pos, file_size, output_path)
        else:
            await self._extract_parallel(start_pos, file_size, output_path)

    async def _extract_sequential_compressed(self, start_pos, file_size, output_path):
        end_pos = start_pos + file_size
        decompressor = zlib.decompressobj(-zlib.MAX_WBITS)
        
        with open(output_path, 'wb') as f:
            cur = start_pos
            while cur < end_pos:
                chunk_size = min(4 * 1024 * 1024, end_pos - cur)
                data = await self.client.fetch_range(cur, cur + chunk_size)
                f.write(decompressor.decompress(data))
                cur += chunk_size
            f.write(decompressor.flush())

    async def _extract_parallel(self, start_pos, file_size, output_path):
        with open(output_path, "wb") as f:
            f.truncate(file_size)

        if file_size == 0:
            return

        fd = os.open(output_path, os.O_RDWR)
        
        try:
            mm = mmap.mmap(fd, file_size)
        except Exception:
            os.close(fd)
            await self._extract_sequential_raw(start_pos, file_size, output_path)
            return

        chunk_size = 4 * 1024 * 1024
        tasks = []
        sem = asyncio.Semaphore(self.client.concurrency)

        async def worker(file_offset, url_offset, size):
            async with sem:
                data = await self.client.fetch_range(url_offset, url_offset + size)
                mm[file_offset : file_offset + size] = data

        for i in range(0, file_size, chunk_size):
            size = min(chunk_size, file_size - i)
            tasks.append(worker(i, start_pos + i, size))

        try:
            await asyncio.gather(*tasks)
        finally:
            mm.close()
            os.close(fd)

    async def _extract_sequential_raw(self, start_pos, file_size, output_path):
        end_pos = start_pos + file_size
        with open(output_path, 'wb') as f:
            cur = start_pos
            while cur < end_pos:
                chunk_size = min(4 * 1024 * 1024, end_pos - cur)
                data = await self.client.fetch_range(cur, cur + chunk_size)
                f.write(data)
                cur += chunk_size
