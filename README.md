# Video Overlay

Corta vídeos gravados no celular na proporção de cada rede social e aplica
overlays (bordas nos cantos + logo em um deles) usando **ffmpeg**.

## Arquitetura

```
Interface (web hoje / Telegram amanhã)
        │ enfileira job
        ▼
Fila (Celery + Redis)
        │
        ▼
Core (puro, só ffmpeg)  ── não conhece web nem Telegram
```

- **`app/core/`** — núcleo de processamento, independente de interface:
  - `presets.py` — proporções por rede (adicionar rede = adicionar entrada).
  - `overlays.py` — overlays como dados (4 cantos x {logo, borda}).
  - `ffmpeg_builder.py` — monta o comando ffmpeg (crop/scale + overlays + fade).
  - `processor.py` — executa ffmpeg/ffprobe (com timeout e validação) e devolve o vídeo.
  - `errors.py` — `ProcessingError`, exceção com a causa real do ffmpeg.
  - `schemas.py` — contrato `ProcessRequest` (serializável p/ a fila).
- **`app/worker/`** — Celery + Redis (processamento assíncrono).
- **`app/web/`** — FastAPI (upload, status, download).
- **`app/bot/`** — bot do Telegram (aiogram), usa a MESMA task da web.
- **`assets/overlays/`** — PNGs (ver README de lá).

## Como o vídeo é encaixado na proporção (escala / fundo)

Vídeos de celular vêm em proporções variadas (e às vezes em proporção
"errada" — ex.: um iPhone antigo gerando vídeo vertical marcado como
horizontal). Para encaixar qualquer entrada na proporção da rede sem que o
ffmpeg quebre, o pipeline **sempre escala primeiro e força as dimensões
finais exatas do preset** (que são pares — requisito do `libx264`/`yuv420p`,
que rejeita largura/altura ímpar). Com isso não há erro de dimensão, seja
fazendo *upscale* de um vídeo de baixa resolução, seja *downscale* de um 4K.

Quando a proporção da entrada **não bate** com a da rede, há duas
estratégias, escolhidas pelo campo `fit_mode`:

### 1. `crop` (cortar — padrão)
Escala cobrindo todo o quadro (`force_original_aspect_ratio=increase`) e
**corta o excesso**. Não sobra borda, mas perde conteúdo nas pontas. A
posição do corte é configurável via `crop_gravity`: `center`, `top` ou
`bottom`. Ideal quando a proporção da entrada é parecida com a do alvo.

### 2. `blur` (fundo borrado)
Mostra o **vídeo inteiro, sem cortar**, sobreposto a um fundo que é o próprio
vídeo ampliado para cobrir o quadro e **desfocado** (`gblur`). Preenche as
sobras sem barras pretas e sem perder conteúdo — é o que Instagram/TikTok
fazem com vídeos fora de proporção. Resolve exatamente o caso "vídeo vertical
em proporção horizontal" (e o inverso). O grafo é:

```
[0:v]split=2[bg][fg];
[bg] scale (cobre) -> crop -> gblur      # fundo borrado preenchendo o quadro
[fg] scale (cabe inteiro, decrease)      # vídeo completo, sem corte
[bg][fg] overlay=(W-w)/2:(H-h)/2         # centraliza a frente sobre o fundo
```

> **Por que não usamos barras pretas (letterbox/pillarbox simples)?**
> Porque pedido foi preencher com fundo: o `blur` ocupa as sobras com uma
> versão desfocada do próprio vídeo, ficando mais agradável que barras pretas
> e mantendo 100% do conteúdo visível. Se um dia quiser barras sólidas, basta
> trocar o ramo `[bg]` por um `pad` com cor fixa.

Validado com proporções extremas (landscape 320x180 → 9:16 e vertical
480x854 → 16:9), nos dois modos, sem erro e com saída sempre nas dimensões
exatas do preset.

## Pré-requisitos

- Python 3.11+
- **ffmpeg** e **ffprobe** instalados no sistema (`ffmpeg -version`)
- **Redis** rodando (ex.: `docker run -p 6379:6379 redis`)

## Instalação

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Executar com Docker (recomendado)

Sobe Redis + worker + web + bot de uma vez (ffmpeg já vem na imagem):

```bash
docker compose up --build
```

O token do bot é lido do `.env` (`TELEGRAM_BOT_TOKEN=...`). Web em
http://localhost:8000. Os serviços compartilham os volumes `storage/` e
`assets/`, então upload e processamento usam os mesmos arquivos.

## Executar manualmente (3 processos)

```bash
# 1) Redis (se ainda não estiver rodando)
docker run -p 6379:6379 redis

# 2) Worker Celery
celery -A app.worker.celery_app:celery_app worker --loglevel=info

# 3) Web (FastAPI)
uvicorn app.web.main:app --reload

# OU, no lugar da web, o bot do Telegram (precisa de TELEGRAM_BOT_TOKEN):
python -m app.bot.main
```

Acesse http://localhost:8000 (web). O bot e a web compartilham o mesmo
worker — basta ter o Celery rodando.

## Limites, validação e limpeza

Configuráveis por variáveis de ambiente (ver `.env.example`):

- **Upload**: extensão precisa estar em `ALLOWED_VIDEO_EXTENSIONS`; tamanho
  limitado por `MAX_UPLOAD_MB` (web rejeita em streaming, bot checa pelo
  `file_size` do Telegram).
- **Duração**: vídeos acima de `MAX_DURATION_SECONDS` são recusados (checado
  após o `ffprobe`).
- **Timeout**: cada job tem no máximo `FFMPEG_TIMEOUT_SECONDS`; se estourar,
  vira `ProcessingError` em vez de travar o worker.
- **Erros do ffmpeg**: o `stderr` real é logado e devolvido na mensagem de
  falha (antes se perdia na exceção crua).
- **Limpeza**: a task `cleanup_old_files` (Celery beat, a cada
  `CLEANUP_INTERVAL_SECONDS`) apaga arquivos de `uploads/`/`outputs/` mais
  antigos que `RETENTION_HOURS`. No Docker, o worker já roda com `-B` (beat
  embarcado).

## Testes

```bash
pip install -r requirements-dev.txt
pytest
```

Cobrem o core puro (montagem do comando ffmpeg: crop/blur/fade/posição,
`-loop` nas imagens, dimensões) e a validação do processor (duração, timeout,
erro de ffmpeg) — sem precisar executar o ffmpeg de verdade.

## Lint e formatação

Usamos **ruff** (lint + format) e **pre-commit** — tudo local, sem amarrar a
nenhuma plataforma de CI.

```bash
pip install -r requirements-dev.txt
ruff check .          # lint
ruff format .         # formata
pre-commit install    # opcional: roda ruff a cada git commit
```

Config em `pyproject.toml`. O `B008` é ignorado em `app/web/main.py` (padrão
do FastAPI) e o `UP042` globalmente (mantemos `(str, Enum)` por causa da
serialização).

## Próximos passos

- **Overlays animados**: trocar PNG por `.webm` (VP9 com alpha) ou `.mov`
  (ProRes 4444); só muda o `asset_path`.
- **Notificação push**: hoje o bot faz polling do resultado; dá para trocar
  por uma fila de callbacks do Celery se o volume crescer.
