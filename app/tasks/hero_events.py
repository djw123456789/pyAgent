import logging

logger = logging.getLogger(__name__)


def record_hero_event(action: str, hero_id: int) -> None:
    logger.info("[hero_event] action=%s hero_id=%s", action, hero_id)