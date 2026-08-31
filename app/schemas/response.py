from pydantic import BaseModel
from typing import Generic, TypeVar,Optional, Any

class ErrorResponse(BaseModel):
    code: int           # 业务状态码（非 HTTP 状态码），如 1001 表示用户不存在
    message: str        # 友好的错误提示
    detail: Optional[Any] = None  # 详细的错误堆栈或字段校验信息（仅开发环境）

T = TypeVar('T')

class SuccessResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "success"
    data: Optional[T] = None