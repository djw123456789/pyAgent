import logging
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.cache import redis_client


logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):

    def __init__(
        self,
        app,
        calls_per_minute: int = 10,
    ):
        super().__init__(app)

        self.calls_per_minute = calls_per_minute
        self.window_seconds = 60


    async def dispatch(
        self,
        request: Request,
        call_next,
    ):
        client_ip = (
            request.client.host
            if request.client
            else "unknown"
        )

        now = time.time()

        # 当前属于哪个 60 秒窗口
        window_id = int(
            now // self.window_seconds
        )

        key = (
            f"rate_limit:"
            f"{client_ip}:"
            f"{window_id}"
        )

        try:
            # 本窗口请求次数 +1
            count = await redis_client.incr(key)

            # 设置过期时间。
            # 多给一倍时间只是为了自动清理旧窗口 key。
            await redis_client.expire(
                key,
                self.window_seconds * 2,
            )

        except Exception:
            logger.warning(
                "[rate-limit] Redis unavailable, "
                "request allowed"
            )

            return await call_next(request)


        # 超过限制
        if count > self.calls_per_minute:

            retry_after = (
                self.window_seconds
                - int(now % self.window_seconds)
            )

            return JSONResponse(
                status_code=429,
                content={
                    "detail": (
                        "请求过于频繁，"
                        f"每分钟限制 "
                        f"{self.calls_per_minute} 次"
                    )
                },
                headers={
                    "Retry-After": str(retry_after)
                },
            )


        return await call_next(request)