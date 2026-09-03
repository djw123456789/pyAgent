"""
Redis 缓存与分布式锁。

功能：
1. Redis 全局异步客户端
2. Cache-Aside 基础操作
3. TTL 随机抖动，降低缓存雪崩风险
4. Redis 分布式锁
5. Lua 安全释放分布式锁
"""

import json
import logging
import random
import uuid

import redis.asyncio as aioredis

from app.core.config import settings


logger = logging.getLogger(__name__)


# =========================================================
# Redis 客户端
# =========================================================

redis_client: aioredis.Redis = aioredis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=50,
)


# =========================================================
# Redis 分布式锁
# =========================================================

# 只有锁里的 token 和当前调用者 token 一致时才允许删除
RELEASE_LOCK_SCRIPT = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
else
    return 0
end
"""


async def acquire_lock(
    key: str,
    ttl: int = 5,
) -> str | None:
    """
    尝试获取 Redis 分布式锁。

    成功：
        返回当前锁唯一 token

    失败：
        返回 None

    SET NX：
        key 不存在时才能创建

    EX：
        给锁设置超时时间，避免死锁
    """

    token = str(uuid.uuid4())

    try:
        acquired = await redis_client.set(
            key,
            token,
            nx=True,
            ex=ttl,
        )

        if acquired:
            logger.debug(
                "[lock] acquired key=%s token=%s",
                key,
                token,
            )
            return token

        return None

    except Exception:
        logger.warning(
            "[lock] acquire failed key=%s",
            key,
        )
        return None


async def release_lock(
    key: str,
    token: str,
) -> int:
    """
    安全释放 Redis 分布式锁。

    使用 Lua 保证：
        GET token
        判断 token
        DEL key

    三个步骤作为一个原子操作执行。
    """

    try:
        released = await redis_client.eval(
            RELEASE_LOCK_SCRIPT,
            1,
            key,
            token,
        )

        logger.debug(
            "[lock] release key=%s released=%s",
            key,
            released,
        )

        return released

    except Exception:
        logger.warning(
            "[lock] release failed key=%s",
            key,
        )
        return 0


# =========================================================
# Cache-Aside
# =========================================================

async def cache_get(key: str):
    """
    读取缓存。

    HIT：
        返回反序列化后的对象

    MISS：
        返回 None

    Redis 故障：
        降级为 MISS，让业务继续查数据库
    """

    try:
        raw = await redis_client.get(key)

        if raw is None:
            logger.info(
                "[cache_get] MISS key=%s",
                key,
            )
            return None

        logger.info(
            "[cache_get] HIT key=%s",
            key,
        )

        return json.loads(raw)

    except Exception:
        logger.warning(
            "[cache_get] GET failed, "
            "fallback to database key=%s",
            key,
        )

        return None


async def cache_set(
    key: str,
    data,
    ttl: int | None = None,
):
    """
    写入缓存。

    TTL 加随机抖动：
        降低大量缓存同时失效造成的缓存雪崩。
    """

    try:
        base_ttl = (
            ttl
            if ttl is not None
            else settings.CACHE_TTL
        )

        jittered_ttl = max(
            1,
            int(
                base_ttl
                * random.uniform(0.8, 1.2)
            ),
        )

        await redis_client.set(
            key,
            json.dumps(data),
            ex=jittered_ttl,
        )

        logger.info(
            "[cache_set] SET key=%s ttl=%ss",
            key,
            jittered_ttl,
        )

    except Exception:
        logger.warning(
            "[cache_set] SET failed key=%s",
            key,
        )


async def cache_delete(*keys: str):
    """
    删除一个或多个缓存 key。
    """

    try:
        if not keys:
            return

        deleted = await redis_client.delete(
            *keys
        )

        logger.info(
            "[cache_delete] DELETE keys=%s deleted=%s",
            keys,
            deleted,
        )

    except Exception:
        logger.warning(
            "[cache_delete] DELETE failed keys=%s",
            keys,
        )


# =========================================================
# Redis 生命周期
# =========================================================

async def close_redis():
    """
    FastAPI 关闭时释放 Redis 连接池。
    """

    await redis_client.aclose()