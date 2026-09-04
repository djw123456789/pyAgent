import asyncio

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)
from app.tasks.hero_events import record_hero_event
from typing import List, Optional

from sqlmodel.ext.asyncio.session import (
    AsyncSession,
)

from app.core.database import get_session

from app.core.cache import (
    cache_get,
    cache_set,
    cache_delete,
    acquire_lock,
    release_lock,
)

from app.crud import hero as hero_crud

from app.models.hero import Hero
from app.models.user import User

from app.api.deps import (
    get_current_user,
    get_hero_by_id,
)

from app.schemas.response import SuccessResponse


router = APIRouter()


# 数据库不存在时缓存的空值哨兵
NULL_SENTINEL = {
    "__null__": True
}


# =========================================================
# GET Hero 列表
# =========================================================

@router.get(
    "/",
    response_model=SuccessResponse[List[Hero]],
)
async def read_heroes(
    name: Optional[str] = None,
    session: AsyncSession = Depends(
        get_session
    ),
):
    heroes = await hero_crud.get_all(
        session,
        name,
    )

    return SuccessResponse(
        data=heroes
    )


# =========================================================
# GET Hero 详情
#
# Cache-Aside
# +
# NULL_SENTINEL 防缓存穿透
# +
# Redis Distributed Lock 防缓存击穿
# +
# Double-Check
# =========================================================

@router.get(
    "/{hero_id}",
    response_model=SuccessResponse[Hero],
)
async def read_hero(
    hero_id: int,
    session: AsyncSession = Depends(
        get_session
    ),
):
    cache_key = f"hero:{hero_id}"
    lock_key = f"lock:{cache_key}"


    # -----------------------------------------------------
    # ① 无锁快查缓存
    # -----------------------------------------------------

    cached = await cache_get(
        cache_key
    )

    # 命中“不存在”缓存
    if cached == NULL_SENTINEL:
        raise HTTPException(
            status_code=404,
            detail="英雄不存在",
        )

    # 正常 Cache HIT
    if cached is not None:
        return SuccessResponse(
            data=cached
        )


    # -----------------------------------------------------
    # ② Cache MISS
    # 尝试获取 Redis 分布式锁
    # -----------------------------------------------------

    token = await acquire_lock(
        lock_key,
        ttl=5,
    )


    # -----------------------------------------------------
    # ③ 成功获得锁
    # 当前请求负责查询 DB + 回填缓存
    # -----------------------------------------------------

    if token:

        try:

            # Double-Check
            #
            # 获取锁之前可能已经有其他 Worker
            # 完成数据库查询并写入缓存。

            cached = await cache_get(
                cache_key
            )

            if cached == NULL_SENTINEL:
                raise HTTPException(
                    status_code=404,
                    detail="英雄不存在",
                )

            if cached is not None:
                return SuccessResponse(
                    data=cached
                )
            # -------------------------------------------------
            # 真正查询数据库
            # -------------------------------------------------
            hero = await hero_crud.get_by_id(
                session,
                hero_id,
            )
            # -------------------------------------------------
            # 数据库也不存在
            #
            # 写 NULL_SENTINEL 防缓存穿透
            # -------------------------------------------------
            if not hero:

                await cache_set(
                    cache_key,
                    NULL_SENTINEL,
                    ttl=30,
                )

                raise HTTPException(
                    status_code=404,
                    detail="英雄不存在",
                )
            # -------------------------------------------------
            # 数据库存在
            #
            # 回填 Redis
            # -------------------------------------------------
            await cache_set(
                cache_key,
                hero.model_dump(
                    mode="json"
                ),
            )

            return SuccessResponse(
                data=hero
            )


        finally:

            # 无论：
            #
            # 正常返回
            # 404
            # 数据库异常
            #
            # 都尽力释放自己的锁。

            await release_lock(
                lock_key,
                token,
            )


    # -----------------------------------------------------
    # ④ 没拿到锁
    #
    # 说明可能有其他 Worker
    # 正在查询 DB 并准备回填缓存。
    #
    # 不要直接再次查询 DB。
    # -----------------------------------------------------

    for _ in range(20):

        # 等待 50ms
        await asyncio.sleep(
            0.05
        )

        # 看其他 Worker
        # 是否已经完成缓存回填
        cached = await cache_get(
            cache_key
        )

        if cached == NULL_SENTINEL:
            raise HTTPException(
                status_code=404,
                detail="英雄不存在",
            )

        if cached is not None:
            return SuccessResponse(
                data=cached
            )


    # -----------------------------------------------------
    # ⑤ 等待约 1 秒仍然没有缓存
    #
    # 这里选择数据库兜底，
    # 避免 Redis 锁异常导致业务完全不可用。
    # -----------------------------------------------------

    hero = await hero_crud.get_by_id(
        session,
        hero_id,
    )

    if not hero:
        raise HTTPException(
            status_code=404,
            detail="英雄不存在",
        )

    # 尝试重新写缓存。
    # Redis 故障时 cache_set 自己会降级。
    await cache_set(
        cache_key,
        hero.model_dump(
            mode="json"
        ),
    )

    return SuccessResponse(
        data=hero
    )


# =========================================================
# POST 创建 Hero
# =========================================================

@router.post("/", response_model=Hero, status_code=201)
async def create_hero(
    hero: Hero,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    created = await hero_crud.create(session, hero, current_user.id)
    await cache_delete(f"hero:{created.id}")

    record_hero_event.delay(
        "created",
        created.id,
    )

    return created


# =========================================================
# PUT 更新 Hero
# =========================================================
@router.put("/{hero_id}", response_model=Hero)
async def update_hero(
    updated_data: Hero,
    session: AsyncSession = Depends(get_session),
    hero: Hero = Depends(get_hero_by_id),
):
    result = await hero_crud.update(session, hero.id, updated_data)
    await cache_delete(f"hero:{hero.id}")

    record_hero_event.delay(
        "updated",
        hero.id,
    )

    return result


# =========================================================
# DELETE Hero
# =========================================================
@router.delete("/{hero_id}", status_code=204)
async def delete_hero(
    session: AsyncSession = Depends(get_session),
    hero: Hero = Depends(get_hero_by_id),
):
    hero_id = hero.id

    await hero_crud.delete(session, hero_id)
    await cache_delete(f"hero:{hero_id}")

    record_hero_event.delay(
        "deleted",
        hero_id,
    )

    return None