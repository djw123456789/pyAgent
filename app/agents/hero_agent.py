from agents import Agent, Runner
from agents.decorators import tool

from app.core.database import async_session_maker
from app.core.llm import deepseek_model
from app.crud.hero import get_all, get_by_id
import logging

logger = logging.getLogger(__name__)

@tool
async def get_hero(hero_id: int) -> str:
    """根据英雄 ID 查询英雄信息。"""
    logger.info("[agent_tool] get_hero hero_id=%s", hero_id)

    async with async_session_maker() as session:
        hero = await get_by_id(session, hero_id)

        if not hero:
            return "英雄不存在"

        return hero.model_dump_json()

@tool
async def list_heroes() -> str:
    """查询数据库中的所有英雄。"""
    async with async_session_maker() as session:
        heroes = await get_all(session)

        return str([
            hero.model_dump(mode="json")
            for hero in heroes
        ])

hero_agent = Agent(
    name="Hero Assistant",
    instructions=(
        "你是 pyAgent 的英雄助手。"
        "当用户询问数据库中的英雄数据时必须调用工具查询，"
        "不要编造数据库中不存在的数据。"
    ),
    model=deepseek_model,
    tools=[
        get_hero,
        list_heroes,
    ],
)

async def run_hero_agent(message: str) -> str:
    result = await Runner.run(
        hero_agent,
        message,
    )

    return str(result.final_output)