"""Interface web (FastAPI).

Fluxo: usuário sobe o vídeo -> enfileira um job -> recebe job_id na hora.
Depois consulta o status e baixa o resultado quando pronto. O bot do
Telegram, no futuro, vai chamar exatamente a mesma task `process_video_task`.
"""

import uuid
from pathlib import Path

from celery.result import AsyncResult
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from app import settings
from app.core.overlays import Corner
from app.core.presets import PRESETS
from app.core.schemas import ProcessRequest
from app.worker.celery_app import celery_app
from app.worker.tasks import process_video_task

app = FastAPI(title="Video Overlay")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    # Assinatura atual do Starlette: request primeiro, depois o nome do template.
    return templates.TemplateResponse(
        request,
        "index.html",
        {"presets": list(PRESETS.values()), "corners": list(Corner)},
    )


@app.post("/jobs")
async def create_job(
    video: UploadFile = File(...),
    preset_key: str = Form(...),
    logo_corner: Corner = Form(Corner.BOTTOM_RIGHT),
    fit_mode: str = Form("crop"),
    crop_gravity: str = Form("center"),
    hidden_borders: list[str] = Form(default=[]),
    margin: int = Form(40),
    border_fade_in: float = Form(0.0),
    border_fade_out: float = Form(0.0),
):
    if preset_key not in PRESETS:
        raise HTTPException(400, f"Preset inválido: {preset_key}")

    # Valida a extensão antes de salvar.
    suffix = Path(video.filename or "video.mp4").suffix.lower() or ".mp4"
    if suffix not in settings.ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            400,
            f"Formato {suffix} não suportado. Aceitos: "
            f"{', '.join(sorted(settings.ALLOWED_VIDEO_EXTENSIONS))}",
        )

    # Salva o upload com nome único, abortando se exceder o tamanho máximo
    # (lido em blocos para não carregar o arquivo inteiro na memória).
    input_path = settings.UPLOADS_DIR / f"{uuid.uuid4().hex}{suffix}"
    written = 0
    with input_path.open("wb") as f:
        while chunk := video.file.read(1024 * 1024):
            written += len(chunk)
            if written > settings.MAX_UPLOAD_BYTES:
                f.close()
                input_path.unlink(missing_ok=True)
                raise HTTPException(413, f"Arquivo maior que {settings.MAX_UPLOAD_MB} MB.")
            f.write(chunk)

    req = ProcessRequest(
        input_path=str(input_path),
        preset_key=preset_key,
        logo_corner=logo_corner,
        fit_mode=fit_mode,
        crop_gravity=crop_gravity,
        hidden_borders=hidden_borders,
        margin=margin,
        border_fade_in=border_fade_in,
        border_fade_out=border_fade_out,
    )
    task = process_video_task.delay(req.model_dump(mode="json"))
    return {"job_id": task.id}


@app.get("/jobs/{job_id}")
def job_status(job_id: str):
    result = AsyncResult(job_id, app=celery_app)
    payload = {"job_id": job_id, "status": result.status}
    if result.failed():
        payload["error"] = str(result.result)
    return payload


@app.get("/jobs/{job_id}/download")
def job_download(job_id: str):
    result = AsyncResult(job_id, app=celery_app)
    if not result.successful():
        raise HTTPException(409, f"Job ainda não concluído (status: {result.status})")
    output = Path(result.result)
    if not output.exists():
        raise HTTPException(404, "Arquivo de saída não encontrado")
    return FileResponse(output, media_type="video/mp4", filename=output.name)
