import aiohttp
import asyncio

class NetworkManager:
    def __init__(self, url, concurrency=16):
        self.url = url
        self.concurrency = concurrency
        self.connector = aiohttp.TCPConnector(limit=0, ttl_dns_cache=3000, force_close=False, ssl=False)
        self.session = None
        self.file_size = 0

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            connector=self.connector,
            headers={
                "User-Agent": "fcetool",
                "Accept-Encoding": "identity" 
            }
        )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()

    async def get_size(self):
        try:
            async with self.session.head(self.url, allow_redirects=True) as resp:
                accept_ranges = resp.headers.get("Accept-Ranges", "none")
                if accept_ranges == "none":
                    raise Exception(
                        f"Server does not support Range requests. "
                        f"Accept-Ranges: {accept_ranges}. "
                    )
                
                if resp.status == 200:
                    self.file_size = int(resp.headers.get("Content-Length", 0))                    
                    return self.file_size

            async with self.session.get(self.url, headers={"Range": "bytes=0-0"}, allow_redirects=True) as resp:
                if resp.status in [200, 206]:
                    val = resp.headers.get("Content-Range", "").split("/")
                    self.file_size = int(val[1]) if len(val) > 1 else int(resp.headers.get("Content-Length", 0))
                    return self.file_size
                raise Exception(f"HTTP {resp.status}")
        except Exception as e:
            raise Exception(f"Connection Failed: {e}")

    async def fetch_range(self, start, end, retries=3):
        headers = {"Range": f"bytes={start}-{end-1}"}
        for attempt in range(retries):
            try:
                async with self.session.get(self.url, headers=headers, allow_redirects=True) as resp:
                    if resp.status == 206:
                        return await resp.read()
                    elif resp.status == 200:
                        raise Exception(
                            f"Server does not support Range requests. "
                            f"Server returned HTTP 200 instead of 206 Partial Content. "
                            f"Requested range: {start}-{end-1}"
                        )
                    else:
                        raise Exception(f"HTTP {resp.status}")
            except Exception:
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(1)


class SubFileClient:
    def __init__(self, parent_client, offset, size):
        self.parent = parent_client
        self.offset = offset
        self.size = size
        self.concurrency = parent_client.concurrency

    async def get_size(self):
        return self.size

    async def fetch_range(self, start, end):
        real_start = self.offset + start
        real_end = self.offset + end
        return await self.parent.fetch_range(real_start, real_end)