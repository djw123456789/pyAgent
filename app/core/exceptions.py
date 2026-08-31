from typing import Any, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import logging

class AppException(Exception):
    """所有自定义异常的基类"""
    def __init__(
        self,
        code: int,
        message: str,
        status_code: int = 400,
        detail: Optional[Any] = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(message)

# 具体的业务异常（类似 Java 的 @ResponseStatus）
class NotFoundException(AppException):
    def __init__(self, message: str = "资源不存在", detail: Any = None):
        super().__init__(code=404, message=message, status_code=404, detail=detail)

class PermissionDeniedException(AppException):
    def __init__(self, message: str = "权限不足", detail: Any = None):
        super().__init__(code=403, message=message, status_code=403, detail=detail)

class BadRequestException(AppException):
    def __init__(self, message: str = "请求参数错误", detail: Any = None):
        super().__init__(code=400, message=message, status_code=400, detail=detail)

class UnauthorizedException(AppException):
    def __init__(self, message: str = "未登录或 Token 失效", detail: Any = None):
        super().__init__(code=401, message=message, status_code=401, detail=detail)

logger = logging.getLogger(__name__)

# 处理我们自定义的 AppException
async def app_exception_handler(request: Request, exc: AppException):
    logger.error(f"业务异常: {exc.message}, code: {exc.code}, detail: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "detail": exc.detail
        }
    )

# 处理 FastAPI 自带的请求校验异常（422）
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"参数校验失败: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": 422,
            "message": "请求参数校验失败",
            "detail": exc.errors()  # 自动提供详细的字段错误
        }
    )

# 处理所有未捕获的数据库异常（防止暴露 SQL 语句）
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.exception(f"数据库错误: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": 500,
            "message": "服务器内部错误，请稍后重试",
            "detail": None  # 不暴露敏感信息
        }
    )

# 兜底处理所有未捕获的异常
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception(f"未知错误: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": 500,
            "message": "服务器内部错误",
            "detail": str(exc) if request.app.debug else None  # 开发模式可展示
        }
    )