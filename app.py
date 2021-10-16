from os import environ
from celery import Celery
from celery.schedules import crontab


environ.setdefault("CELERY_CONFIG_MODULE", "celery_config")

app = Celery()
app.config_from_envvar("CELERY_CONFIG_MODULE")


app.conf.beat_schedule = {
    "every-minute": {
        "task": "app.add",
        "schedule": crontab(),
        "args": (16, 16),
    },
}


@app.task
def add(x, y):
    return x + y
