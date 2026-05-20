# syntax=docker/dockerfile:1.7

FROM python:3.12-alpine

ENV PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/usr/local \
    UV_NO_CACHE=1

WORKDIR /app

RUN --mount=from=ghcr.io/astral-sh/uv:0.11.15,source=/uv,target=/bin/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-dev --no-install-project

COPY src ./src

CMD ["python", "src/sonwet.py"]