FROM python:3.10-slim-bullseye
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID
ENV DEBIAN_FRONTEND=noninteractive \
 PYTHONDONTWRITEBYTECODE 1 \
 PYTHONUNBUFFERED 1 \
 POETRY_VIRTUALENVS_CREATE 0 \
 WATCHFILES_FORCE_POLLING 1 \
 REDIS_HOST "redis"
RUN mkdir /workspace
WORKDIR /workspace
RUN apt-get update \
    && apt-get -y install git libpq-dev gcc libwebp-dev postgresql-client \
    && apt-get -y upgrade \
    && python -m pip install --upgrade pip
RUN pip install 'poetry==1.1.14'
COPY poetry.lock pyproject.toml /workspace/
RUN poetry config virtualenvs.create false
RUN poetry install --no-interaction --no-ansi
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME
ENV DEBIAN_FRONTEND=dialog
USER $USERNAME
RUN mkdir -p /home/$USERNAME/.vscode-server/extensions \
    && chown -R $USERNAME /home/$USERNAME/.vscode-server \
