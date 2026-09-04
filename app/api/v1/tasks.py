from celery.result import AsyncResult
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.celery import celery_app
from app.tasks.hero_events import record_hero_event

router = APIRouter()

class HeroEventRequest(BaseModel):
    action: str
    hero_id: int

@router.post("/hero-events", status_code=202)
async def create_hero_event_task(data: HeroEventRequest):
    task = record_hero_event.delay(
        data.action,
        data.hero_id,
    )

    return {
        "task_id": task.id,
        "status": task.status,
    }

@router.get("/{task_id}")
async def get_task_status(task_id: str):
    task = AsyncResult(
        task_id,
        app=celery_app,
    )

    response = {
        "task_id": task_id,
        "status": task.status,
    }

    if task.successful():
        response["result"] = task.result
    elif task.failed():
        response["error"] = str(task.result)

    return response