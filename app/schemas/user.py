from typing import Optional
from pydantic import BaseModel, EmailStr, Field

# 注册请求体 (相当于 @RequestBody RegisterRequest)
class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=72)

# 登录请求体
class UserLogin(BaseModel):
    username: str
    password: str

# 返回给前端的用户信息 (不包含密码)
class UserOut(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool

    class Config:
        from_attributes = True  # 支持从 SQLModel 对象转换