FROM python:3.11-slim-bullseye
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID
ENV DEBIAN_FRONTEND=noninteractive \
    POETRY_HOME="/opt/poetry" \
    POETRY_NO_INTERACTION=1 \
    POETRY_VERSION=1.4.2 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=0 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SHELL=/bin/bash \
    VIRTUAL_ENV="/home/$USERNAME/.poetry/venv" \
    WATCHFILES_FORCE_POLLING=1
RUN mkdir /workspace /opt/poetry /workspace/media /workspace/static
WORKDIR /workspace
RUN apt-get update && apt-get -y upgrade && apt-get -y install \
    curl \
    git \
    libpq-dev \
    gcc \
    libwebp-dev \
    postgresql-client
RUN python -m pip install --upgrade pip
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && chown -R $USERNAME:$USERNAME /workspace /opt/poetry \
    && chmod -R 777 /workspace
USER $USERNAME
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$POETRY_HOME/bin:$PATH" \
    POETRY_VIRTUALENVS_PATH="$VIRTUAL_ENV"
COPY poetry.lock pyproject.toml /workspace/
RUN poetry install --no-interaction --no-ansi \
    && poetry self add poetry-plugin-up
ENV DEBIAN_FRONTEND=dialog
RUN mkdir -p /home/$USERNAME/.vscode-server/extensions \
    && chown -R $USERNAME /home/$USERNAME/.vscode-server
