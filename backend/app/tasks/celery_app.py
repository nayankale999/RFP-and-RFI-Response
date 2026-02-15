from celery import Celery

from app.config import get_settings

settings = get_settings()

celery = Celery(
    "rfp_automation",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.parse_task",
        "app.tasks.extract_task",
        "app.tasks.generate_task",
    ],
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=300,  # 5 minutes
    task_time_limit=600,  # 10 minutes
)
