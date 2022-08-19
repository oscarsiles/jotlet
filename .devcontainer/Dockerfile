FROM python:3.10-slim-bullseye
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID
ENV DEBIAN_FRONTEND=noninteractive \
    POETRY_VIRTUALENVS_CREATE=0 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SHELL=/bin/bash \
    WATCHFILES_FORCE_POLLING=1
RUN mkdir /workspace
WORKDIR /workspace
RUN apt-get update && apt-get -y upgrade && apt-get -y install \
    git \
    libpq-dev \
    gcc \
    libwebp-dev \
    postgresql-client
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME
RUN python -m pip install --upgrade pip \
    && pip install "poetry==1.1.14"
USER $USERNAME
COPY poetry.lock pyproject.toml /workspace/
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi
ENV DEBIAN_FRONTEND=dialog
RUN mkdir -p /home/$USERNAME/.vscode-server/extensions \
    && chown -R $USERNAME /home/$USERNAME/.vscode-server
