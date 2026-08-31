from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import timedelta
from app.core.database import get_session
from app.core.security import create_access_token, verify_password
from app.crud import user as user_crud
from app.schemas.user import UserCreate, UserLogin, UserOut
from app.schemas.token import Token

router = APIRouter(prefix="/auth", tags=["认证"])

@router.post("/register", response_model=UserOut, status_code=201)
async def register(user_data: UserCreate, session: AsyncSession = Depends(get_session)):
    """用户注册"""
    # 检查用户名是否已存在
    existing_user = await user_crud.get_user_by_username(session, user_data.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已被占用")
    # 检查邮箱是否已存在
    existing_email = await user_crud.get_user_by_email(session, user_data.email)
    if existing_email:
        raise HTTPException(status_code=400, detail="邮箱已被注册")
    # 创建用户（密码会自动哈希）
    new_user = await user_crud.create_user(session, user_data)
    return new_user

@router.post("/login", response_model=Token)
async def login(login_data: UserLogin, session: AsyncSession = Depends(get_session)):
    """用户登录，返回 JWT Token"""
    user = await user_crud.get_user_by_username(session, login_data.username)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    # 生成 Token
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}