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

import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)

# 全局共享的 Redis 客户端（懒连接: 首次使用时才真正建立连接）
redis_client: aioredis.Redis = aioredis.from_url(
    settings.REDIS_URL,
    decode_responses=True,  # 关键! 否则所有返回值都是 b'xxx' 字节串
    max_connections=50,     # 连接池上限, 防止突发流量耗尽 Redis 连接
)


async def cache_get(key: str):
    """
    读缓存: 命中返回反序列化后的对象, 未命中返回 None。
    Redis 故障时降级返回 None（当作 MISS 走数据库）, 绝不让缓存拖垮主业务。
    """
    try:
        raw = await redis_client.get(key)
        return json.loads(raw) if raw else None
    except Exception:
        logger.warning(f"[cache] 读取失败, 降级直查数据库: key={key}")
        return None


async def cache_set(key: str, data, ttl: int | None = None):
    """
    写缓存: 序列化为 JSON 并设置过期时间（默认用配置里的 CACHE_TTL）。

    过期时间加了 ±20% 随机抖动, 防止大量 key 在同一秒集体过期（缓存雪崩）。
    """
    try:
        base = ttl or settings.CACHE_TTL
        jittered = int(base * random.uniform(0.8, 1.2))  # 雪崩解法: TTL 抖动
        await redis_client.set(key, json.dumps(data), ex=jittered)
    except Exception:
        logger.warning(f"[cache] 写入失败（不影响主流程）: key={key}")


async def cache_delete(*keys: str):
    """删缓存: 数据更新后调用, 支持一次删多个 key（8.6 缓存一致性会用到）"""
    try:
        if keys:
            await redis_client.delete(*keys)
    except Exception:
        logger.warning(f"[cache] 删除失败（还有 TTL 兑底）: keys={keys}")


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
