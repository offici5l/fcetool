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
            headers={"User-Agent": "FCE-Client/1.0"}
        )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self.session:
            await self.session.close()

    async def get_size(self):
        try:
            async with self.session.head(self.url) as resp:
                if resp.status == 200:
                    self.file_size = int(resp.headers.get("Content-Length", 0))
                    return self.file_size
            
            async with self.session.get(self.url, headers={"Range": "bytes=0-0"}) as resp:
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
                async with self.session.get(self.url, headers=headers) as resp:
                    if resp.status not in [200, 206]:
                        raise Exception(f"HTTP {resp.status}")
                    return await resp.read()
            except Exception:
                if attempt == retries - 1: raise
                await asyncio.sleep(1)
