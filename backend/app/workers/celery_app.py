from celery import Celery
from app.core.config import settings

celery = Celery(
    "kavach",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery.conf.update(
    timezone="Asia/Kolkata",
    enable_utc=False,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
)

celery.conf.beat_schedule = {
    "risk-monitor-every-10-seconds": {
        "task": "app.workers.risk_monitor.risk_monitor_tick",
        "schedule": 10.0,  # Run every 10 seconds
    }
}

# Autodiscover tasks from the workers directory
celery.autodiscover_tasks(["app.workers"])
