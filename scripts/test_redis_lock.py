import asyncio
import sys
from pathlib import Path

# 直接运行脚本时(scripts/ 不含项目根目录), 把项目根目录加入模块搜索路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.cache import (
    acquire_lock,
    release_lock,
    redis_client,
)


async def main():
    lock_key = "lock:test"

    await redis_client.delete(lock_key)

    token1 = await acquire_lock(
        lock_key,
        ttl=10,
    )

    print(
        "第一次抢锁:",
        token1 is not None,
    )

    token2 = await acquire_lock(
        lock_key,
        ttl=10,
    )

    print(
        "第二次抢锁:",
        token2 is not None,
    )

    if token1:
        released = await release_lock(
            lock_key,
            token1,
        )

        print(
            "释放锁:",
            released,
        )

    token3 = await acquire_lock(
        lock_key,
        ttl=10,
    )

    print(
        "释放后再次抢锁:",
        token3 is not None,
    )

    if token3:
        await release_lock(
            lock_key,
            token3,
        )

    await redis_client.aclose()


if __name__ == "__main__":
    asyncio.run(main())