"""Iterate through our talks and announce them to discord when it's time to go see the talk.

TODO:
1. Decide how we want to do the actual scheduling: celery? event loop like tornado? cron job?
2. Iterate over all the talks and test it in Discord
3. Delete all the announcements before we invite anyone in
"""
from typing import Any, Literal
from pathlib import Path
import datetime
import json
import os
import time

from celery import Celery
import click
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from environs import Env
import frontmatter
from jinja2 import Template
import pytz
import requests
import typer


IGNORED_CATEGORIES = ["break", "lunch", "social-hour"]

CONFERENCE_TZ = pytz.timezone("America/Chicago")
# That 885 number is a reference to the #live-q-and-a channel.
# You can get this ID by sending a discord message of the form "\#channel-name"
# and seeing what posts
MESSAGE_TEMPLATE = """:tada: Talk starting right now: **{post[title]}** by *{speaker}*

:tv: {post[video_url]}

See the talk information at https://2021.djangocon.us{post[permalink]}

Live discussions are happening in <#885229363921043486>.
"""

FIVE_MINUTE_WARNING_TEMPLATE = """:tada: Talk starting in 5 minutes: **{post[title]}** by *{speaker}*

:alarm_clock: Watch the talk at [{timestamp:%H:%M %Z}](https://time.is/compare/{timestamp:%I%M%p_%d_%B_%Y}_in_Chicago)

:tv: {post[video_url]}

See the talk information at https://2021.djangocon.us{post[permalink]}

Live discussions are happening in <#885229363921043486>.
"""

app = Celery("announce_talk")
app.conf.broker_url = os.environ.get("CELERY_BROKER", "redis:///")

cli_app = typer.Typer(help="Awesome Announce Talks")

env = Env()

DRAFT_FOLDER = Path(env("DRAFT_FOLDER", default="_drafts"))
INBOX_FOLDER = Path(env("INBOX_FOLDER", default="_inbox"))
OUTBOX_FOLDER = Path(env("OUTBOX_FOLDER", default="_outbox"))


def post_about_talks(
    *, path: Path, webhook_url: str, post_now: bool = False
) -> Literal[None]:
    if path.is_dir():
        filenames = path.glob("**/*.md")
        filenames = list(filenames)
        filenames = sorted(filenames)
    else:
        filenames = [path]

    for filename in filenames:
        try:
            post = frontmatter.loads(filename.read_text())
            if post["category"].strip().lower() not in IGNORED_CATEGORIES:
                if isinstance(post["date"], datetime.datetime):
                    timestamp = post["date"]
                else:
                    timestamp = parse(post["date"])
                timestamp = timestamp.astimezone(CONFERENCE_TZ)

                speakers: list[dict] = post.get("presenters", [])
                try:
                    speaker = speakers[0]
                except (IndexError, TypeError):
                    typer.echo(f"No speaker for talk {post['title']}")
                    typer.secho(f"{filename}", fg="red")
                    break

                # TODO queue 5 minute to go message separately from this
                body = {
                    "content": MESSAGE_TEMPLATE.format(
                        post=post,
                        speaker=speaker["name"],
                        video_url=post["video_url"],
                        timestamp=timestamp,
                    ),
                    "allowed_mentions": {
                        "parse": ["everyone"],
                        "users": [],
                    },
                    # "embeds": [
                    #     {
                    #         "type": "rich",
                    #         "title": "Text",
                    #         "description": "Text description here",
                    #     },
                    #     {
                    #         "type": "image",
                    #         "title": "Author image",
                    #         "height": "400",
                    #         "width": "400",
                    #         "url": f"http://2021.djangocon.us{post['image']}",
                    #     },
                    #     {
                    #         "type": "video",
                    #         "title": "Video link",
                    #         "url": f"{post['video_url']}",
                    #     },
                    # ],
                }
                five_to_go_body = {
                    "content": FIVE_MINUTE_WARNING_TEMPLATE.format(
                        post=post,
                        speaker=speaker["name"],
                        timestamp=timestamp,
                    ),
                    "allowed_mentions": {
                        "parse": ["everyone"],
                        "users": [],
                    },
                    # "embeds": [
                    #     {
                    #         "type": "rich",
                    #         "title": "Text",
                    #         "description": "Text description here",
                    #     },
                    #     {
                    #         "type": "image",
                    #         "title": "Author image",
                    #         "height": "400",
                    #         "width": "400",
                    #         "url": f"http://2021.djangocon.us{post['image']}",
                    #     },
                    #     {
                    #         "type": "video",
                    #         "title": "Video link",
                    #         "url": f"{post['video_url']}",
                    #     },
                    # ],
                }

                if webhook_url:
                    if "CELERY_BROKER" in os.environ:
                        # if we're in test mode, pretend all talks are at the 5 minutes to go mark
                        # momentarily
                        post_time = (
                            timestamp
                            if not post_now
                            else pytz.UTC.localize(datetime.datetime.utcnow())
                            + relativedelta(minutes=5, seconds=5)
                        )

                        # Dispatch these off to celery
                        post_to_webhook.s(
                            webhook_url=webhook_url,
                            body=five_to_go_body,
                        ).apply_async(eta=post_time - relativedelta(minutes=5))
                        post_to_webhook.s(
                            webhook_url=webhook_url,
                            body=body,
                        ).apply_async(eta=post_time)
                        if post_now:
                            typer.secho(
                                f'Messages for {post["title"]} queued; Waiting 30 sec before'
                                " queueing next messages"
                            )
                            time.sleep(30)
                    else:
                        post_to_webhook(webhook_url=webhook_url, body=body)
                        time.sleep(30)
                else:
                    typer.echo(f"{body['content']}")
                    typer.echo(json.dumps(body, indent=2))
                    typer.secho("----" * 10, fg="yellow")

        except Exception as e:
            typer.secho(f"{filename}::{e}", fg="red")


@app.task(
    autoretry_for=[requests.exceptions.RequestException],
    retry_backoff=True,
)
def post_to_webhook(*, webhook_url: str, body: dict[str, Any]) -> Literal[None]:
    """Post the body to the webhook URL"""
    response = requests.post(webhook_url, json=body)
    response.raise_for_status()


@cli_app.command()
def main(
    talks_path: Path = typer.Option(
        default="_schedule/talks/", help="Directory where talks are stored"
    ),
    webhook_url: str = typer.Option(
        default=None, help="URL for the webhook to the Q & A channel"
    ),
    post_now: bool = typer.Option(
        default=False,
        help="Pretend the talks are happening now instead of queueing the talks up later "
        "(for testing)",
    ),
):
    if webhook_url and "CELERY_BROKER" not in os.environ:
        typer.secho(
            click.style("Warning: not using celery for posting messages", fg="yellow")
        )
    post_about_talks(path=talks_path, webhook_url=webhook_url, post_now=post_now)


@cli_app.command()
def copy_schedule_to_drafts(
    talks_path: Path = typer.Option(
        default="_schedule/talks/", help="Directory where talks are stored"
    )
):
    if not DRAFT_FOLDER.exists():
        typer.secho(f"DRAFT_FOLDER '{DRAFT_FOLDER}' does not exist", fg="red")
        raise typer.Exit()

    if not talks_path.exists():
        typer.secho(f"talks-path '{talks_path}' does not exist", fg="red")
        raise typer.Exit()

    filenames = sorted(list(talks_path.glob("*.md")))

    for filename in filenames:
        try:
            post = frontmatter.loads(filename.read_text())
            new_post = frontmatter.loads("")

            if isinstance(post["date"], datetime.datetime):
                timestamp = post["date"]
            else:
                timestamp = parse(post["date"])
            timestamp = timestamp.astimezone(CONFERENCE_TZ)

            speakers: list[dict] = post.get("presenters", [])
            try:
                speaker = speakers[0]
            except (IndexError, TypeError):
                typer.echo(f"No speaker for talk {post['title']}")
                typer.secho(f"{filename}", fg="red")
                speaker = None
                # break

            new_post["category"] = post["category"]
            new_post["date"] = post["date"]
            new_post["title"] = post["title"]

            # TODO: we can customize what gets included with Discord
            # new_post["allowed_mentions"] = body["allowed_mentions"]

            # Normal messages...
            template_filename = Path("templates", f"{post['category']}.html")
            if template_filename.exists():
                template = Template(template_filename.read_text())
                context = {
                    "post": post,
                    "speaker": speaker["name"] if speaker else None,
                    "timestamp": timestamp,
                    "video_url": post["video_url"] if "video_url" in post else None,
                }
                output = template.render(context)

                body = {
                    "content": output,
                    "allowed_mentions": {
                        "parse": ["everyone"],
                        "users": [],
                    },
                }

                # Copy only what we need to "new_post"
                new_post.content = body["content"]

                destination = DRAFT_FOLDER.joinpath(filename.name)

                typer.echo(f"copying {filename.name} to {destination.parent}")
                destination.write_text(frontmatter.dumps(new_post))

                # Hack to make timezones stick...
                destination.write_text(frontmatter.dumps(new_post))

            # Five Minutes...
            template_filename = Path(
                "templates", f"{post['category']}-five-minutes.html"
            )
            if template_filename.exists():
                template = Template(template_filename.read_text())
                context = {
                    "post": post,
                    "speaker": speaker["name"] if speaker else None,
                    "timestamp": timestamp,
                    "video_url": post["video_url"] if "video_url" in post else None,
                }
                output = template.render(context)

                body = {
                    "content": output,
                    "allowed_mentions": {
                        "parse": ["everyone"],
                        "users": [],
                    },
                }

                # Copy only what we need to "new_post"
                new_post.content = body["content"]
                new_post["date"] = timestamp - relativedelta(minutes=5, seconds=0)

                # Hack for timezone formatting changing to "-05:00"
                new_post["date"] = str(new_post["date"]).replace("-05:00", " -0500")

                destination = DRAFT_FOLDER.joinpath(
                    str(filename.name).replace(".md", "-five-minutes.md")
                )

                # typer.echo(f"copying {filename.name} to {destination.parent}")
                destination.write_text(frontmatter.dumps(new_post))
                # rewrite_post = frontmatter.loads(destination.read_text())
                # destination.write_text(frontmatter.dumps(rewrite_post))

        except Exception as e:
            typer.secho(f"{filename}::{e}", fg="red")


@cli_app.command()
def process_folder():
    now = datetime.datetime.now().astimezone(CONFERENCE_TZ)
    typer.secho(f"now: {now}", fg="yellow")

    if not DRAFT_FOLDER.exists():
        typer.secho(f"DRAFT_FOLDER '{DRAFT_FOLDER}' does not exist", fg="red")
        raise typer.Exit()

    if not INBOX_FOLDER.exists():
        typer.secho(f"INBOX_FOLDER '{INBOX_FOLDER}' does not exist", fg="red")
        raise typer.Exit()

    if not OUTBOX_FOLDER.exists():
        typer.secho(f"OUTBOX_FOLDER '{OUTBOX_FOLDER}' does not exist", fg="red")
        raise typer.Exit()

    filenames = INBOX_FOLDER.glob("*.md")
    for filename in filenames:
        post = frontmatter.loads(filename.read_text())
        if isinstance(post["date"], datetime.datetime):
            timestamp = post["date"]
        else:
            timestamp = parse(post["date"])

        timestamp = timestamp.astimezone(CONFERENCE_TZ)
        if timestamp <= now:
            typer.secho(f"I would move {filename}", fg="green")


if __name__ == "__main__":
    cli_app()
