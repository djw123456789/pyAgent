import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # 记录请求信息(高频日志用 DEBUG 级, 避免 INFO 级海量日志拖慢性能; 访问日志 uvicorn 已有)
        logger.debug(f"请求开始: {request.method} {request.url.path}")
        
        try:
            response = await call_next(request)
        except Exception as e:
            logger.exception("请求处理异常")
            raise e
        finally:
            process_time = (time.time() - start_time) * 1000
            logger.debug(f"请求完成: {request.method} {request.url.path} - 耗时 {process_time:.2f}ms")
        
        # 在响应头中添加处理时间（方便前端调试）
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
        return response