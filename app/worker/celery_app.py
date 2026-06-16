"""Instância do Celery. Broker e backend de resultado no Redis."""

from celery import Celery

from app import settings

celery_app = Celery(
    "video_overlay",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Limpeza periódica de arquivos antigos (precisa do Celery beat ativo).
    beat_schedule={
        "cleanup-old-files": {
            "task": "cleanup_old_files",
            "schedule": float(settings.CLEANUP_INTERVAL_SECONDS),
        },
    },
)
