# syntax = docker/dockerfile:experimental

FROM python:3.9-slim-buster

ENV PIP_DISABLE_PIP_VERSION_CHECK 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

COPY requirements.txt /app/

WORKDIR /app/

RUN --mount=type=cache,target=/root/.cache/pip pip install --requirement=/app/requirements.txt

ADD . /app/

CMD ["echo", "hello"]
