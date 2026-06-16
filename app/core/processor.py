"""Orquestrador do core: recebe um ProcessRequest, devolve o caminho do vídeo.

É o único ponto que efetivamente executa o ffmpeg/ffprobe. Não sabe nada
sobre web, Telegram ou fila — recebe dados, processa, devolve um arquivo.
"""

import logging
import subprocess
from pathlib import Path

from .errors import ProcessingError
from .ffmpeg_builder import build_command
from .overlays import build_overlay_set
from .presets import get_preset
from .schemas import ProcessRequest

logger = logging.getLogger(__name__)


def _run(cmd: list[str], timeout: float | None) -> subprocess.CompletedProcess:
    """Roda um comando capturando o erro real do ffmpeg/ffprobe.

    Converte falhas em ProcessingError com o final do stderr, em vez de deixar
    a exceção crua do subprocess se perder.
    """
    try:
        return subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise ProcessingError(f"Processamento excedeu o limite de {timeout}s.") from e
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or "").strip()
        logger.error("ffmpeg falhou (%s): %s", cmd[0], stderr)
        # Mantém só o final do stderr, que é onde fica a causa.
        raise ProcessingError(f"{cmd[0]} falhou: {stderr[-500:]}") from e


def probe_duration(path: str, timeout: float | None = 30) -> float:
    """Retorna a duração do vídeo em segundos (via ffprobe)."""
    result = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            path,
        ],
        timeout=timeout,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        raise ProcessingError(
            "Não foi possível ler a duração — arquivo de vídeo inválido?"
        ) from None


def process_video(
    req: ProcessRequest,
    assets_dir: Path,
    output_path: Path,
    *,
    max_duration: float | None = None,
    ffmpeg_timeout: float | None = None,
) -> str:
    """Executa o pipeline completo e devolve o caminho do vídeo final.

    `max_duration` rejeita vídeos longos demais; `ffmpeg_timeout` evita que um
    job trave o worker indefinidamente. Ambos opcionais para manter o core
    utilizável sem configuração.
    """
    preset = get_preset(req.preset_key)
    overlays = build_overlay_set(
        logo_corner=req.logo_corner,
        assets_dir=assets_dir,
        hidden_borders=req.hidden_borders,
        margin=req.margin,
        border_fade_in=req.border_fade_in,
        border_fade_out=req.border_fade_out,
    )

    duration = probe_duration(req.input_path)
    if max_duration is not None and duration > max_duration:
        raise ProcessingError(
            f"Vídeo tem {duration:.0f}s; o máximo permitido é {max_duration:.0f}s."
        )

    cmd = build_command(
        input_path=req.input_path,
        output_path=str(output_path),
        preset=preset,
        overlays=overlays,
        total_duration=duration,
        fit_mode=req.fit_mode,
        crop_gravity=req.crop_gravity,
        crf=req.crf,
    )
    _run(cmd, timeout=ffmpeg_timeout)
    return str(output_path)
