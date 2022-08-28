FROM python:3.10-slim-bullseye
ARG USERNAME=jotlet
ARG USER_UID=1000
ARG USER_GID=$USER_UID
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    REDIS_HOST="redis"
RUN mkdir /app
WORKDIR /app
RUN apt-get update && apt-get -y upgrade && apt-get -y install \
    libpq-dev \
    gcc \
    libwebp-dev
RUN python -m pip install --upgrade pip \
    && pip install "poetry==1.1.15"
COPY poetry.lock pyproject.toml /app/
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME
USER $USERNAME
ADD . /app/
