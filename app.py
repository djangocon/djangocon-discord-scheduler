import requests

from os import environ
from celery import Celery
from celery.schedules import crontab
from environs import Env
from typing import Any, Literal

# from announce_talk import post_about_talks
from process_folder import main as process_folder


environ.setdefault("CELERY_CONFIG_MODULE", "celery_config")

app = Celery()
app.config_from_envvar("CELERY_CONFIG_MODULE")

env = Env()


app.conf.beat_schedule = {
    "every-minute": {
        "task": "app.add",
        "schedule": crontab(),
        "args": (16, 16),
    },
    "process-folder": {
        "task": "app.schedule_process_folder",
        "schedule": crontab(),
    },
}


@app.task
def add(x, y):
    return x + y


@app.task(
    autoretry_for=[requests.exceptions.RequestException],
    retry_backoff=True,
)
def schedule_process_folder():
    process_folder()


@app.task(
    autoretry_for=[requests.exceptions.RequestException],
    retry_backoff=True,
)
def post_to_webhook(*, webhook_url: str, body: dict[str, Any]) -> Literal[None]:
    """Post the body to the webhook URL"""
    response = requests.post(webhook_url, json=body)
    response.raise_for_status()
