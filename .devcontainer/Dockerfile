FROM python:3.10-slim-bullseye
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV REDIS_HOST "redis"
RUN mkdir /workspace
WORKDIR /workspace
RUN apt-get update \
    && apt-get -y install git libpq-dev gcc libwebp-dev postgresql-client
COPY ../requirements.txt /workspace/
RUN pip install -r requirements.txt
COPY ../requirements-dev.txt /workspace/
RUN pip install -r requirements-dev.txt
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME
ENV DEBIAN_FRONTEND=dialog
USER $USERNAME
RUN mkdir -p /home/$USERNAME/.vscode-server/extensions \
    && chown -R $USERNAME /home/$USERNAME/.vscode-server \
