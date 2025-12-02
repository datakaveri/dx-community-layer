import redis.asyncio as redis

from .env_config import env_config

# ------------------------------------------------------------------------------
# Redis Configuration
# ------------------------------------------------------------------------------


redis_client = redis.Redis.from_url(env_config.REDIS_URL, decode_responses=True)
