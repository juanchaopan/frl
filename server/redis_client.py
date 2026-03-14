import os

from redis.asyncio import Redis

_client: Redis | None = None


async def get_redis() -> Redis:
    global _client
    if _client is None:
        url = os.environ.get("REDIS_URL")
        if not url:
            raise ValueError("Missing required environment variable: REDIS_URL")
        _client = Redis.from_url(url)
    return _client
