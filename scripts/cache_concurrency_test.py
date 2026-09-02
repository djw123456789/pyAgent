import asyncio
import time

import httpx


URL = "http://127.0.0.1:8000/api/v1/heroes/1"
CONCURRENCY = 10


async def request_hero(client, request_id):
    start = time.perf_counter()

    response = await client.get(URL)

    elapsed = time.perf_counter() - start

    print(
        f"请求 {request_id}: "
        f"status={response.status_code}, "
        f"time={elapsed:.2f}s"
    )


async def main():
    async with httpx.AsyncClient(timeout=20) as client:

        start = time.perf_counter()

        tasks = [
            request_hero(client, i)
            for i in range(1, CONCURRENCY + 1)
        ]

        await asyncio.gather(*tasks)

        elapsed = time.perf_counter() - start

        print(f"\n总耗时: {elapsed:.2f}s")


if __name__ == "__main__":
    asyncio.run(main())