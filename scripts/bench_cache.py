"""
8.8 缓存性能对比压测: 缓存命中(详情接口) vs 直查数据库(列表接口)

用法: 先启动服务(uvicorn app.main:app --port 8000), 再运行:
    uv run python scripts/bench_cache.py
"""
import asyncio
import time

import httpx

BASE = "http://127.0.0.1:8000/api/v1"
N = 300            # 每组总请求数
CONCURRENCY = 50   # 并发数


async def run_batch(client: httpx.AsyncClient, url: str):
    """并发打一批请求, 返回(客户端延迟ms列表, 服务端处理耗时ms列表)"""
    sem = asyncio.Semaphore(CONCURRENCY)
    latencies: list[float] = []
    server_times: list[float] = []

    async def one():
        async with sem:
            t0 = time.perf_counter()
            resp = await client.get(url)
            latencies.append((time.perf_counter() - t0) * 1000)
            assert resp.status_code == 200, f"HTTP {resp.status_code}"
            # 日志中间件埋的服务端真实处理耗时(不含排队等待), 排除环境干扰
            raw = resp.headers.get("X-Process-Time", "0ms").removesuffix("ms")
            server_times.append(float(raw))

    await asyncio.gather(*[one() for _ in range(N)])
    return latencies, server_times


def report(label: str, latencies: list[float], server_times: list[float], wall: float):
    latencies.sort()
    server_times.sort()
    avg = sum(latencies) / len(latencies)
    srv_avg = sum(server_times) / len(server_times)
    srv_p95 = server_times[int(len(server_times) * 0.95)]
    print(
        f"{label:<20} | 吞吐 {N / wall:6.0f} req/s | "
        f"客户端延迟 平均 {avg:6.1f}ms | "
        f"服务端耗时 平均 {srv_avg:6.2f}ms P95 {srv_p95:6.2f}ms"
    )


async def main():
    async with httpx.AsyncClient() as client:
        # 预热: 确保英雄3的缓存已存在(冷启动的第一个请求不算成绩)
        warm = await client.get(f"{BASE}/heroes/3")
        assert warm.status_code == 200, "预热失败, 请确认英雄 id=3 存在且服务已启动"

        cases = [
            ("直查数据库(列表接口)", f"{BASE}/heroes/"),   # 每次都查库
            ("缓存命中(详情接口)", f"{BASE}/heroes/3"),    # 每次走 Redis
        ]
        results = {}
        for label, url in cases:
            t0 = time.perf_counter()
            latencies, server_times = await run_batch(client, url)
            wall = time.perf_counter() - t0
            results[label] = (wall, server_times)
            report(label, latencies, server_times, wall)

        db_srv = sum(results["直查数据库(列表接口)"][1]) / N
        cache_srv = sum(results["缓存命中(详情接口)"][1]) / N
        print(f"\n>>> 服务端处理耗时提升: {db_srv / cache_srv:.1f} 倍 "
              f"({db_srv:.2f}ms -> {cache_srv:.2f}ms)")


if __name__ == "__main__":
    asyncio.run(main())
