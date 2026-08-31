from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.database import get_session
from app.core.cache import cache_get, cache_set, cache_delete, get_cache_lock
from app.crud import hero as hero_crud
from app.models.hero import Hero
from app.api.deps import get_current_user, get_hero_by_id
from app.models.user import User
from app.schemas.response import SuccessResponse

router = APIRouter()

# 1. GET 列表（保持公开或可选认证）
@router.get("/", response_model=SuccessResponse[List[Hero]])
async def read_heroes(
    name: Optional[str] = None,
    session: AsyncSession = Depends(get_session)
):
    heroes = await hero_crud.get_all(session, name)
    return SuccessResponse(data=heroes)

# 1.5 GET 详情 —— Cache-Aside 完整版（防穿透 + 防击穿）
# 空值哨兵: 专门表示"数据库里确认不存在", 与"缓存未命中"区分开
NULL_SENTINEL = {"__null__": True}


@router.get("/{hero_id}", response_model=SuccessResponse[Hero])
async def read_hero(
    hero_id: int,
    session: AsyncSession = Depends(get_session),
):
    cache_key = f"hero:{hero_id}"  # key 设计: 业务:标识

    # ① 无锁快查缓存 —— 绝大多数请求在这里就返回了, 不需要碰锁
    cached = await cache_get(cache_key)
    if cached == NULL_SENTINEL:
        raise HTTPException(status_code=404, detail="英雄不存在")  # 穿透解法: 命中空值缓存
    if cached is not None:
        return SuccessResponse(data=cached)  # 命中! 不碰数据库

    # ② MISS: 拿这个 key 专属的锁（防击穿, 同一时刻只放一个请求去查库）
    lock = get_cache_lock(cache_key)
    async with lock:
        # ③ 双重检查: 排队期间可能已有别的协程查完库并回填了缓存
        cached = await cache_get(cache_key)
        if cached == NULL_SENTINEL:
            raise HTTPException(status_code=404, detail="英雄不存在")
        if cached is not None:
            return SuccessResponse(data=cached)

        # ④ 队首请求: 真正去查数据库
        hero = await hero_crud.get_by_id(session, hero_id)
        if not hero:
            # 穿透解法: 把"不存在"这个事实也缓存住, 用短TTL(30秒)
            await cache_set(cache_key, NULL_SENTINEL, ttl=30)
            raise HTTPException(status_code=404, detail="英雄不存在")

        # ⑤ 回填缓存(mode="json" 保证日期等类型可序列化)
        await cache_set(cache_key, hero.model_dump(mode="json"))

        return SuccessResponse(data=hero)

# 2. POST 创建（owner_id 自动填充）
@router.post("/", response_model=Hero, status_code=201)
async def create_hero(
    hero: Hero,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    # 此时 current_user 已经拿到，我们调用 crud 时传入 owner_id
    return await hero_crud.create(session, hero, current_user.id)

# 3. PUT 更新（直接依赖 get_hero_by_id，自动完成权限校验）
@router.put("/{hero_id}", response_model=Hero)
async def update_hero(
    updated_data: Hero,
    session: AsyncSession = Depends(get_session),
    hero: Hero = Depends(get_hero_by_id)   # 注意：这里 hero 已经是带权限校验的对象
):
    # 因为 get_hero_by_id 已经校验了所有权，这里直接更新即可
    result = await hero_crud.update(session, hero.id, updated_data)
    # 写路径: 先更新数据库（上面已做），再删除缓存，下次读会回填新数据
    await cache_delete(f"hero:{hero.id}")
    return result

# 4. DELETE 删除（同样的方式）
@router.delete("/{hero_id}", status_code=204)
async def delete_hero(
    session: AsyncSession = Depends(get_session),
    hero: Hero = Depends(get_hero_by_id)   # 权限校验自动完成
):
    await hero_crud.delete(session, hero.id)
    # 英雄删了，缓存必须跟着删，否则会出现"幽灵英雄"（查详情还能查到）
    await cache_delete(f"hero:{hero.id}")
    return None