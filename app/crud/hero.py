from sqlmodel import select, delete
from sqlmodel.ext.asyncio.session import AsyncSession
from app.models.hero import Hero

async def get_all(session: AsyncSession, name: str | None = None):
    query = select(Hero)
    if name:
        query = query.where(Hero.name.contains(name))
    result = await session.execute(query)
    return result.scalars().all()

async def get_by_id(session: AsyncSession, hero_id: int):
    return await session.get(Hero, hero_id)

# app/crud/hero.py 中的 create 函数
async def create(session: AsyncSession, hero_data: Hero, owner_id: int) -> Hero:
    db_hero = Hero(
        name=hero_data.name,
        secret_name=hero_data.secret_name,
        age=hero_data.age,
        owner_id=owner_id   # 必须赋值
    )
    session.add(db_hero)
    await session.commit()
    await session.refresh(db_hero)
    return db_hero

async def update(session: AsyncSession, hero_id: int, updated_data: Hero):
    hero = await get_by_id(session, hero_id)
    if not hero:
        return None
    hero.name = updated_data.name
    hero.secret_name = updated_data.secret_name
    hero.age = updated_data.age
    session.add(hero)
    await session.commit()
    await session.refresh(hero)
    return hero

async def delete(session: AsyncSession, hero_id: int):
    hero = await get_by_id(session, hero_id)
    if hero:
        await session.delete(hero)
        await session.commit()
        return True
    return False

async def delete_all(session: AsyncSession):
    await session.execute(delete(Hero))
    await session.commit()