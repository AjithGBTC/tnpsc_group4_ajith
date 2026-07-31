from celery import Celery
from app.core.config import get_settings

celery_app = Celery("exam_platform", broker=get_settings().redis_url, backend=get_settings().redis_url)
celery_app.conf.update(task_serializer="json", result_serializer="json", accept_content=["json"], timezone="Asia/Kolkata")

@celery_app.task
def refresh_leaderboards() -> None:
    """Schedule this task after attempt submission; aggregation is intentionally idempotent."""
