"""Testes da validação do processor (sem executar ffmpeg de verdade)."""

import subprocess

import pytest

from app.core import processor
from app.core.errors import ProcessingError
from app.core.schemas import ProcessRequest


def _req():
    return ProcessRequest(input_path="in.mp4", preset_key="reels")


def test_rejeita_video_mais_longo_que_o_maximo(monkeypatch, assets_dir):
    monkeypatch.setattr(processor, "probe_duration", lambda *a, **k: 600.0)
    with pytest.raises(ProcessingError, match="máximo"):
        processor.process_video(_req(), assets_dir, assets_dir / "out.mp4", max_duration=300)


def test_erro_do_ffmpeg_vira_processing_error(monkeypatch):
    def boom(*a, **k):
        raise subprocess.CalledProcessError(1, "ffmpeg", stderr="algo deu errado")

    monkeypatch.setattr(subprocess, "run", boom)
    with pytest.raises(ProcessingError, match="ffmpeg falhou"):
        processor._run(["ffmpeg", "-i", "x"], timeout=10)


def test_timeout_vira_processing_error(monkeypatch):
    def slow(*a, **k):
        raise subprocess.TimeoutExpired("ffmpeg", 5)

    monkeypatch.setattr(subprocess, "run", slow)
    with pytest.raises(ProcessingError, match="excedeu"):
        processor._run(["ffmpeg"], timeout=5)


def test_probe_invalido_vira_processing_error(monkeypatch):
    monkeypatch.setattr(
        processor, "_run", lambda *a, **k: subprocess.CompletedProcess([], 0, "lixo", "")
    )
    with pytest.raises(ProcessingError, match="inválido"):
        processor.probe_duration("x.mp4")
