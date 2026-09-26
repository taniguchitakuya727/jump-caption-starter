FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONUTF8=1
ENV PYTHONIOENCODING=utf-8
ENV JUMP_CAPTION_HOST=0.0.0.0
ENV JUMP_CAPTION_PORT=8000

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY app ./app

RUN python -m pip install --upgrade pip \
    && python -m pip install .

RUN mkdir -p uploads outputs

EXPOSE 8000

CMD ["python", "-m", "app"]
