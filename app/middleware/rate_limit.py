import time
from collections import defaultdict
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

# 存储 IP 的请求记录：{ip: [timestamp1, timestamp2, ...]}
request_records = defaultdict(list)

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, calls_per_minute: int = 10):
        super().__init__(app)
        self.calls_per_minute = calls_per_minute
        self.window_seconds = 60

    async def dispatch(self, request: Request, call_next):
        # 获取客户端 IP（注意代理的情况，这里简化处理）
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        
        # 获取该 IP 的历史请求时间戳
        timestamps = request_records[client_ip]
        # 清除超出时间窗口的记录
        timestamps[:] = [t for t in timestamps if now - t < self.window_seconds]
        
        # 检查是否超限
        if len(timestamps) >= self.calls_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"请求过于频繁，请稍后重试（每分钟限制 {self.calls_per_minute} 次）"
            )
        
        # 记录本次请求
        timestamps.append(now)
        
        # 继续处理请求
        response = await call_next(request)
        return response