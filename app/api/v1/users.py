from fastapi import APIRouter, Depends
from app.schemas.user import UserOut
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/users", tags=["用户管理"])

@router.get("/me", response_model=UserOut)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息 (相当于 @GetMapping("/me") + @AuthenticationPrincipal)"""
    return current_user