FROM python:3.10-slim-bullseye
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV REDIS_HOST "redis"
RUN mkdir /app
WORKDIR /app
RUN apt-get update \
    && apt-get -y upgrade \
    && apt-get -y install libpq-dev gcc libwebp-dev
COPY poetry.lock pyproject.toml /app/
RUN poetry config virtualenvs.create false
RUN poetry install --no-dev --no-interaction --no-ansi
ADD . /app/
