"""Configurações de ambiente da aplicação.

Tudo que é "ambiente" (URLs, caminhos) fica aqui, isolado do core de
processamento. O core não importa este módulo — ele recebe caminhos prontos.
"""

import os
from pathlib import Path

# Raiz do projeto (.../claudecode-test-alura)
BASE_DIR = Path(__file__).resolve().parent.parent

# Carrega variáveis do .env (não versionado), se python-dotenv estiver
# disponível. É opcional de propósito: o core roda só com a stdlib.
try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ModuleNotFoundError:
    pass

# Onde ficam os PNGs de overlay, por convenção de nome (ver core/overlays.py)
ASSETS_DIR = Path(os.getenv("ASSETS_DIR", BASE_DIR / "assets" / "overlays"))

# Armazenamento de entrada (uploads) e saída (vídeos processados)
UPLOADS_DIR = Path(os.getenv("UPLOADS_DIR", BASE_DIR / "storage" / "uploads"))
OUTPUTS_DIR = Path(os.getenv("OUTPUTS_DIR", BASE_DIR / "storage" / "outputs"))

# Fila de jobs (Celery + Redis)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Bot do Telegram (obtenha o token com o @BotFather)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# --- Limites e validação ---------------------------------------------------
# Tamanho máximo de upload (MB) e duração máxima do vídeo (segundos).
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "200"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
MAX_DURATION_SECONDS = int(os.getenv("MAX_DURATION_SECONDS", "300"))
# Extensões de vídeo aceitas no upload.
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"}
# Tempo máximo que o ffmpeg pode rodar por job, em segundos.
FFMPEG_TIMEOUT_SECONDS = int(os.getenv("FFMPEG_TIMEOUT_SECONDS", "600"))

# --- Limpeza automática ----------------------------------------------------
# Arquivos em uploads/outputs mais antigos que isso são apagados.
RETENTION_HOURS = int(os.getenv("RETENTION_HOURS", "24"))
# De quanto em quanto tempo a limpeza roda (segundos).
CLEANUP_INTERVAL_SECONDS = int(os.getenv("CLEANUP_INTERVAL_SECONDS", "3600"))

# Garante que os diretórios de trabalho existam
for _d in (UPLOADS_DIR, OUTPUTS_DIR):
    _d.mkdir(parents=True, exist_ok=True)
