FROM python:3.12-slim

# ffmpeg/ffprobe são o motor do processamento — precisam estar na imagem.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instala dependências primeiro para aproveitar o cache de camadas.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Comando padrão (sobrescrito por cada serviço no docker-compose).
CMD ["uvicorn", "app.web.main:app", "--host", "0.0.0.0", "--port", "8000"]
