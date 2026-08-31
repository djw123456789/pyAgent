from typing import Optional
from fastapi import Depends, HTTPException, status, Path
from app.models.hero import Hero
from fastapi.security import APIKeyHeader
from sqlmodel.ext.asyncio.session import AsyncSession
from app.crud import hero as hero_crud
from app.core.database import get_session
from app.core.security import decode_access_token
from app.crud import user as user_crud
from app.models.user import User
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 改用 APIKeyHeader，让 Swagger UI 显示文本输入框
oauth2_scheme = APIKeyHeader(name="Authorization", auto_error=False)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session)
) -> User:
    if not token:
        logger.warning("未提供 Authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 如果 token 格式为 "Bearer xxx"，提取实际 token
    if token.startswith("Bearer "):
        token = token[7:]  # 去掉 "Bearer " 前缀
    
    try:
        payload = decode_access_token(token)
        username = payload.get("sub")
        if not username:
            logger.error("Token 缺少 sub 字段")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的认证凭据",
            )
        
        user = await user_crud.get_user_by_username(session, username)
        if not user:
            logger.error(f"用户不存在: {username}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在",
            )
        return user
    except Exception as e:
        logger.exception("认证失败")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证失败，请检查 Token 是否有效",
        )

async def get_hero_by_id(
    hero_id: int = Path(..., title="英雄ID", ge=1),  # 直接从路径参数提取
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> Hero:
    """
    获取英雄，同时校验当前用户是否为该英雄的创建者。
    校验失败自动抛出 404 或 403，无需路由层再写 if。
    """
    hero = await hero_crud.get_by_id(session, hero_id)
    if not hero:
        raise HTTPException(status_code=404, detail="英雄不存在")
    
    # 如果英雄没有 owner_id，允许访问（向后兼容），否则必须匹配
    if hero.owner_id is not None and hero.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您不是该英雄的创建者，无权操作"
        )
    return hero