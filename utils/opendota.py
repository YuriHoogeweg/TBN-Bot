import asyncio
from io import BytesIO

import aiohttp
from PIL import Image

from config import Configuration

OPENDOTA_BASE = "https://api.opendota.com/api"
STEAM_CDN = "https://cdn.cloudflare.steamstatic.com"


class RateLimiter:
    """Sliding-window rate limiter. Allows `calls` requests per `period` seconds."""
    def __init__(self, calls: int, period: float):
        self._sem = asyncio.Semaphore(calls)
        self._period = period

    async def __aenter__(self):
        await self._sem.acquire()
        return self

    async def __aexit__(self, *_):
        asyncio.get_running_loop().call_later(self._period, self._sem.release)


_OPENDOTA_LIMITER: RateLimiter | None = None


def get_limiter() -> RateLimiter:
    global _OPENDOTA_LIMITER
    if _OPENDOTA_LIMITER is None:
        key = Configuration.instance().OPENDOTA_KEY
        _OPENDOTA_LIMITER = RateLimiter(calls=2950 if key else 55, period=60.0)
    return _OPENDOTA_LIMITER


async def get_json(session: aiohttp.ClientSession, url: str) -> list | dict:
    key = Configuration.instance().OPENDOTA_KEY
    if key:
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}api_key={key}"
    async with get_limiter():
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            resp.raise_for_status()
            return await resp.json()


async def fetch_image(
    session: aiohttp.ClientSession,
    url: str,
    size: tuple[int, int] | None = None,
) -> Image.Image | None:
    """Fetch an image from a URL (or CDN-relative path starting with '/') and optionally resize."""
    if not url:
        return None
    if url.startswith("/"):
        url = f"{STEAM_CDN}{url}"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                return None
            data = await resp.read()
            img = Image.open(BytesIO(data)).convert("RGBA")
            if size is not None:
                img = img.resize(size, Image.LANCZOS)
            return img
    except Exception:
        return None
