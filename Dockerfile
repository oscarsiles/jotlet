FROM ghcr.io/astral-sh/uv:0.4.5-python3.12-bookworm-slim

WORKDIR /app

ARG USERNAME=jotlet
ARG USER_UID=1000
ARG USER_GID=$USER_UID

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

RUN apt-get update && apt-get -y upgrade && apt-get -y install \
    gcc \
    libpq-dev \
    libwebp-dev \
    python3-dev

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME

USER $USERNAME

ENV PATH="/app/.venv/bin:$PATH"

ADD . /app/

ENTRYPOINT []
