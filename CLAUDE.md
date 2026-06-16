# CLAUDE.md

Guia para a IA (e devs) retomarem o projeto rapidamente.

## O que é

Corta vídeos gravados no celular na proporção de cada rede social e aplica
overlays (logo em um canto + bordas nos outros), usando **ffmpeg**. Interface
hoje por web; bot do Telegram já implementado para uso futuro.

## Arquitetura (princípio central: core desacoplado)

```
Interface (web FastAPI / bot aiogram)  ──enfileira──▶  Fila (Celery+Redis)  ──▶  Core (puro, só ffmpeg)
```

- `app/core/` — **núcleo puro, não conhece web/Telegram/fila**. Recebe dados,
  devolve um arquivo.
  - `presets.py` — proporções por rede (add rede = add entrada).
  - `overlays.py` — overlays como **dados** (4 cantos × {logo, borda}); `Corner`.
  - `ffmpeg_builder.py` — monta o comando ffmpeg (função **pura**, não executa).
  - `processor.py` — único ponto que executa ffmpeg/ffprobe (timeout + validação).
  - `errors.py` — `ProcessingError`. `schemas.py` — `ProcessRequest` (serializável).
- `app/worker/` — Celery + Redis; task `process_video_task` + `cleanup_old_files`.
- `app/web/` — FastAPI (upload/status/download). `app/bot/` — aiogram.
- Web e bot montam o MESMO `ProcessRequest` e chamam a MESMA task.

## Decisões importantes (não reverter sem motivo)

- **ffmpeg via `subprocess` direto**, sem wrapper — filtergraphs complexos.
- **Overlays = PNG estático**; fade in/out é feito no ffmpeg. O **logo não faz
  fade** (fica visível sempre, serve de thumbnail); só as bordas fazem fade.
- **Encaixe na proporção** (`fit_mode`): `crop` (corta) ou `blur` (fundo borrado
  estilo Instagram, para proporções extremas). `crop_gravity`: center/top/bottom.
- **`(str, Enum)`** em `Corner` é proposital (serialização) — ruff `UP042` ignorado.
- Limites/limpeza via env (ver `.env.example`); core recebe limites por parâmetro.

## Gotchas

- **PNG no overlay precisa de `-loop 1 -t <duração>`** — imagem é 1 frame em t=0;
  sem loop o `fade` zera o alpha e o overlay some. (Já tratado no builder.)
- **Dimensões finais sempre pares** (presets) — `libx264`/`yuv420p` rejeita ímpar.
- **`.env` tem o token do bot e NÃO é versionado** — nunca commitar segredos.

## Comandos

```bash
# Dev local (3 processos): Redis + worker + web/bot
docker run -p 6379:6379 redis
celery -A app.worker.celery_app:celery_app worker -B --loglevel=info
uvicorn app.web.main:app --reload          # web
python -m app.bot.main                      # OU bot (precisa de TELEGRAM_BOT_TOKEN)

# Tudo via Docker
docker compose up --build

# Testes / lint / format
pytest
ruff check .
ruff format .

# Regenerar PNGs placeholder
python tools/make_placeholders.py
```

## Pré-requisitos

Python 3.11+, **ffmpeg/ffprobe** no sistema, **Redis**. Deps: `requirements.txt`
(runtime) e `requirements-dev.txt` (pytest/ruff/pre-commit).

## Roadmap

- Configurar git remote (hoje sem remote).
- CI **adiada** — preferência por tooling local/agnóstico, sem GitHub Actions.
- Overlays animados: trocar PNG por `.webm` (VP9 com alpha) ou `.mov` (ProRes 4444)
  — só muda o `asset_path`.
- Trocar PNGs placeholder pelos da marca real; mais presets de rede.
