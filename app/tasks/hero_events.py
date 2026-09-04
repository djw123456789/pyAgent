import logging

from app.core.celery import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(
    bind=True,
    name="hero.record_event",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def record_hero_event(self, action: str, hero_id: int) -> dict:
    logger.info(
        "[hero_event] task_id=%s action=%s hero_id=%s",
        self.request.id,
        action,
        hero_id,
    )
    return {
        "action": action,
        "hero_id": hero_id,
    }