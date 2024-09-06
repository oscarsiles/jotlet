FROM ghcr.io/astral-sh/uv:0.4.5-python3.12-bookworm-slim

WORKDIR /app
ADD . /app/

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_CACHE_DIR=/tmp/.uv-cache

RUN apt-get update && apt-get -y upgrade && apt-get -y install \
    gcc \
    libpq-dev \
    libwebp-dev \
    python3-dev

RUN --mount=type=cache,target=/tmp/.uv-cache \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

ENV PATH="/app/.venv/bin:$PATH"

ENTRYPOINT []
