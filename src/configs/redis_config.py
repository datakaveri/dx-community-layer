from redis.asyncio import Redis
from redis.asyncio.cluster import RedisCluster
from redis.asyncio.sentinel import Sentinel

from .env_config import env_config

# ------------------------------------------------------------------------------
# Redis Configuration
# ------------------------------------------------------------------------------

if env_config.REDIS_SENTINEL_ENABLED:
    # The client returned by master_for() asks the sentinels for the current
    # master on connect and re-resolves it after a failover, so it can be used
    # exactly like a standalone client.
    #
    # The timeouts matter: without them a call on a connection to a master that
    # has hung (rather than closed the socket) blocks forever and never gets to
    # the re-resolve step, so the client would not follow the failover.
    redis_sentinel = Sentinel(
        env_config.redis_sentinel_nodes,
        sentinel_kwargs={
            "username": env_config.REDIS_SENTINEL_USERNAME,
            "password": env_config.REDIS_SENTINEL_PASSWORD,
            "socket_timeout": 1,
            "socket_connect_timeout": 1,
        },
        username=env_config.REDIS_USERNAME,
        password=env_config.REDIS_PASSWORD,
        db=env_config.REDIS_DB,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
    )
    redis_client = redis_sentinel.master_for(env_config.REDIS_SENTINEL_MASTER_NAME)
elif env_config.REDIS_CLUSTER_ENABLED:
    redis_client = RedisCluster.from_url(env_config.REDIS_URL, decode_responses=True)
else:
    redis_client = Redis.from_url(env_config.REDIS_URL, decode_responses=True)
