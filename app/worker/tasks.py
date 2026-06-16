"""Tarefas assíncronas. Casca fina sobre o core — só adapta para a fila."""

import logging
import time
from pathlib import Path

from app import settings
from app.core.processor import process_video
from app.core.schemas import ProcessRequest
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="process_video")
def process_video_task(request_data: dict) -> str:
    """Recebe o pedido serializado, processa e devolve o caminho do output.

    O nome do arquivo de saída usa o id da própria task, garantindo unicidade
    e permitindo que a interface localize o resultado pelo job_id.
    """
    req = ProcessRequest(**request_data)
    job_id = process_video_task.request.id
    output_path = settings.OUTPUTS_DIR / f"{job_id}.mp4"
    return process_video(
        req,
        assets_dir=Path(settings.ASSETS_DIR),
        output_path=output_path,
        max_duration=settings.MAX_DURATION_SECONDS,
        ffmpeg_timeout=settings.FFMPEG_TIMEOUT_SECONDS,
    )


@celery_app.task(name="cleanup_old_files")
def cleanup_old_files() -> int:
    """Apaga uploads/outputs mais antigos que RETENTION_HOURS. Roda no beat."""
    cutoff = time.time() - settings.RETENTION_HOURS * 3600
    removed = 0
    for directory in (settings.UPLOADS_DIR, settings.OUTPUTS_DIR):
        for path in Path(directory).iterdir():
            if path.is_file() and path.name != ".gitkeep" and path.stat().st_mtime < cutoff:
                path.unlink()
                removed += 1
    if removed:
        logger.info("Limpeza: %d arquivo(s) antigo(s) removido(s).", removed)
    return removed
