FROM python:3.10-slim-bullseye
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV REDIS_HOST "redis"
RUN mkdir /app
WORKDIR /app
RUN apt-get update \
    && apt-get -y install libpq-dev gcc
COPY requirements.txt /app/
RUN pip install -r requirements.txt
ADD . /app/
