from redis.asyncio import Redis
from redis.asyncio.cluster import RedisCluster

from .env_config import env_config

# ------------------------------------------------------------------------------
# Redis Configuration
# ------------------------------------------------------------------------------

if env_config.REDIS_CLUSTER_ENABLED:
    redis_client = RedisCluster.from_url(env_config.REDIS_URL, decode_responses=True)
else:
    redis_client = Redis.from_url(env_config.REDIS_URL, decode_responses=True)
