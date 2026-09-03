"""
Redis 缓存客户端（全局单例）。

设计要点:
1. from_url + ConnectionPool: 连接池复用连接, 避免每次请求都握手
2. decode_responses=True: 自动把 bytes 解码成 str, 免去手动 .decode()
3. 模块级单例: 整个应用共享一个客户端, redis-py 内部保证连接池线程/协程安全
"""
import asyncio
import json
import logging
import random
import uuid

import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)

# 全局共享的 Redis 客户端（懒连接: 首次使用时才真正建立连接）
redis_client: aioredis.Redis = aioredis.from_url(
    settings.REDIS_URL,
    decode_responses=True,  # 关键! 否则所有返回值都是 b'xxx' 字节串
    max_connections=50,     # 连接池上限, 防止突发流量耗尽 Redis 连接
)

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
):
    token = str(uuid.uuid4())

    acquired = await redis_client.set(
        key,
        token,
        nx=True,
        ex=ttl,
    )

    if acquired:
        return token

    return None

async def release_lock(
    key: str,
    token: str,
):
    return await redis_client.eval(
        RELEASE_LOCK_SCRIPT,
        1,
        key,
        token,
    )

async def cache_get(key: str):
    """
    读取缓存：
    - HIT：返回反序列化对象
    - MISS：返回 None
    - Redis 故障：降级为 MISS
    """
    try:
        raw = await redis_client.get(key)

        if raw is None:
            logger.info("[cache_get] MISS key=%s", key)
            return None

        logger.info("[cache_get] HIT key=%s", key)
        return json.loads(raw)

    except Exception:
        logger.warning(
            "[cache_get] GET failed, fallback to database key=%s",
            key,
        )
        return None


async def cache_set(key: str, data, ttl: int | None = None):
    """
    写入缓存并设置 TTL。
    TTL 加随机抖动，降低缓存雪崩风险。
    """
    try:
        base = ttl or settings.CACHE_TTL
        jittered = int(base * random.uniform(0.8, 1.2))

        await redis_client.set(
            key,
            json.dumps(data),
            ex=jittered,
        )

        logger.info(
            "[cache_set] SET key=%s ttl=%ss",
            key,
            jittered,
        )

    except Exception:
        logger.warning(
            "[cache_set] SET failed key=%s",
            key,
        )

async def cache_delete(*keys: str):
    try:
        if not keys:
            return

        deleted = await redis_client.delete(*keys)

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


# ---------- 缓存击穿解法: per-key 互斥锁(single-flight) ----------
# 同一时刻同一个 key 只允许一个协程去查库回填, 其他协程排队等结果。
# 注: 这是单进程锁; 多实例部署时需换 Redis 分布式锁(SET NX)
_key_locks: dict[str, asyncio.Lock] = {}


def get_cache_lock(key: str) -> asyncio.Lock:
    """获取某个缓存 key 专属的锁（不存在则创建）"""
    if key not in _key_locks:
        _key_locks[key] = asyncio.Lock()
    return _key_locks[key]


async def close_redis():
    """应用关闭时优雅释放连接池, 避免 'Unclosed connection' 警告和连接泄漏"""
    await redis_client.aclose()
