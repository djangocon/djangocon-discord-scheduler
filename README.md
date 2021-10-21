# README

## tl;dw (too long; didn't write one yet)

### Building for Docker Compose

```shell
# setup our env variables
$ cp .docker-env-dist .docker-env

# cat environment variables to see if anything is missing
$ cat .docker-env-dist
BROKER_URL=redis://redis:6379/0
RESULT_BACKEND=redis://redis:6379/0
DISCORD_WEBHOOK=
DRAFT_FOLDER=/app/_drafts
INBOX_FOLDER=/app/_inbox
OUTBOX_FOLDER=/app/_outbox

# to build
$ DOCKER_BUILDKIT=1 docker-compose build

# to start
$ docker-compose up --detach

# to stop
$ docker-compose down
```

### Files

```shell
$ ls *.py
announce_talk.py
app.py
celery_config.py
copy_schedule_to_drafts.py
process_folder.py
```

#### app.py + celery_config.py

`app.py` is our main Celery application and has all of our tasks and our celery beat schedules.

`celery_config.py` is our main settings file for passing in the `BROKER_URL` and `RESULT_BACKEND`.

#### announce_talk.py

This was Drew's original script for publishing messages to Discord. (I don't think we are using this.)

#### copy_schedule_to_drafts.py

`copy_schedule_to_drafts.py` will read from our `_schedule/talks/` folder and create Discord-friendly messages and reminders. This is only called from the command line.

#### process_folder.py

`process_folder.py` is what manages our reading of files from `_inbox`, posting those to Discord, and then moving them to the `_outbox` folder. This is called from Celery.
