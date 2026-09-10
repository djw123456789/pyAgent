from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.models.user import User
from app.services.knowledge import index_document, search_knowledge
from app.services.knowledge import (
    ask_knowledge,
    index_document,
    search_knowledge,
)

router = APIRouter()

class DocumentRequest(BaseModel):
    title: str
    content: str

@router.post("/documents", status_code=201)
async def create_document(
    request: DocumentRequest,
    current_user: User = Depends(get_current_user),
):
    return await index_document(
        request.title,
        request.content,
        current_user.id,
    )

@router.get("/search")
async def search(
    q: str,
    current_user: User = Depends(get_current_user),
):
    return await search_knowledge(
        q,
        current_user.id,
    )

class AskRequest(BaseModel):
    question: str

@router.post("/ask")
async def ask(
    request: AskRequest,
    current_user: User = Depends(get_current_user),
):
    return await ask_knowledge(
        request.question,
        current_user.id,
    )