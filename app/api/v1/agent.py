from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.hero_agent import run_hero_agent

router = APIRouter()

class AgentRequest(BaseModel):
    message: str

@router.post("/chat")
async def chat(request: AgentRequest):
    answer = await run_hero_agent(request.message)

    return {
        "answer": answer,
    }