# syntax=docker/dockerfile:1.7
# Stage 1: Build virtual environment dependencies
FROM python:3.12-slim-bookworm AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --upgrade pip && \
    pip install hatchling && \
    pip install --prefix=/install .

# Stage 2: Final minimal production runtime image
FROM python:3.12-slim-bookworm AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/app" \
    PATH="/install/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Security: Create non-root system group and user
RUN groupadd -g 10001 saasgroup && \
    useradd -u 10001 -g saasgroup -s /sbin/nologin -d /app saasuser

COPY --from=builder /install /install
COPY --chown=saasuser:saasgroup . /app
COPY --chown=saasuser:saasgroup docker/entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

USER saasuser

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--lifespan", "on"]