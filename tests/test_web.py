"""Smoke tests da camada web (FastAPI), sem subir Redis/worker.

Pega regressões de renderização como a da assinatura do TemplateResponse,
que não aparecem em teste de import nem rodando só o core.
"""

from fastapi.testclient import TestClient

from app.web.main import app

client = TestClient(app)


def test_home_renderiza_com_opcoes():
    r = client.get("/")
    assert r.status_code == 200
    # O template precisa renderizar as opções vindas do core.
    assert "Reels" in r.text  # preset
    assert "Fundo borrado" in r.text  # fit_mode
    assert "top_left" in r.text  # canto


def test_upload_rejeita_extensao_invalida():
    r = client.post(
        "/jobs",
        data={"preset_key": "reels"},
        files={"video": ("nota.txt", b"nao sou video", "text/plain")},
    )
    assert r.status_code == 400


def test_upload_rejeita_preset_invalido():
    r = client.post(
        "/jobs",
        data={"preset_key": "inexistente"},
        files={"video": ("v.mp4", b"x", "video/mp4")},
    )
    assert r.status_code == 400
