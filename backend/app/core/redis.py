import aioredis
import json
from app.core.config import settings

# Create Redis connection pool
async def get_redis_pool():
    return await aioredis.from_url(
        f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}",
        encoding="utf-8",
        decode_responses=True
    )

# Cache helpers
async def get_cache(key):
    redis = await get_redis_pool()
    value = await redis.get(key)
    await redis.close()
    
    if value:
        return json.loads(value)
    return None

async def set_cache(key, value, expiration=settings.CACHE_EXPIRATION):
    redis = await get_redis_pool()
    await redis.setex(key, expiration, json.dumps(value))
    await redis.close()
    
async def delete_cache(key):
    redis = await get_redis_pool()
    await redis.delete(key)
    await redis.close() 