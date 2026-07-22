FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TOKENIZERS_PARALLELISM=false \
    PYTHONWARNINGS=ignore::FutureWarning \
    HF_HOME=/cache/huggingface \
    TRANSFORMERS_CACHE=/cache/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/cache/sentence_transformers

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/

RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

COPY . /app

RUN mkdir -p /cache/huggingface /cache/sentence_transformers && chmod -R 777 /cache

CMD ["python", "efficiency.py", "--help"]