FROM python:3.12-slim-bookworm
ARG USERNAME=jotlet
ARG USER_UID=1000
ARG USER_GID=$USER_UID
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN mkdir /app && chmod a+rwx -R /app
WORKDIR /app
RUN apt-get update && apt-get -y upgrade && apt-get -y install \
    gcc \
    libpq-dev \
    libwebp-dev \
    python3-dev
RUN python -m pip install --upgrade pip \
    && pip install "poetry==1.8.2"
COPY poetry.lock pyproject.toml /app/
RUN poetry config virtualenvs.create false \
    && poetry install --without dev,test --no-interaction --no-ansi
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME
USER $USERNAME
ADD . /app/
