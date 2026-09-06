import logging
from datetime import UTC, datetime

from app.core.celery import celery_app

logger = logging.getLogger(__name__)

@celery_app.task(name="system.heartbeat")
def system_heartbeat() -> dict:
    now = datetime.now(UTC).isoformat()
    logger.info("[system_heartbeat] timestamp=%s", now)
    return {
        "status": "ok",
        "timestamp": now,
    }