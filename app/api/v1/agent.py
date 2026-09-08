from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.agents.hero_agent import run_hero_agent
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter()

class AgentRequest(BaseModel):
    session_id: str
    message: str

@router.post("/chat")
async def chat(
    request: AgentRequest,
    current_user: User = Depends(get_current_user),
):
    session_id = (
        f"user:{current_user.id}:"
        f"conversation:{request.session_id}"
    )

    answer = await run_hero_agent(
        request.message,
        session_id,
    )

    return {
        "session_id": request.session_id,
        "answer": answer,
    }