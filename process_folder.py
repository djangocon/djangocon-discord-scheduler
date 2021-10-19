"""Iterate through our talks and announce them to discord when it's time to go see the talk.

TODO:
1. Decide how we want to do the actual scheduling: celery? event loop like tornado? cron job?
2. Iterate over all the talks and test it in Discord
3. Delete all the announcements before we invite anyone in
"""
from pathlib import Path
import datetime
from dateutil.parser import parse
from environs import Env
import frontmatter
import pytz
import typer


IGNORED_CATEGORIES = ["break", "lunch", "social-hour"]

CONFERENCE_TZ = pytz.timezone("America/Chicago")

app = typer.Typer(help="Awesome Announce Talks")

env = Env()

DRAFT_FOLDER = Path(env("DRAFT_FOLDER", default="_drafts"))
INBOX_FOLDER = Path(env("INBOX_FOLDER", default="_inbox"))
OUTBOX_FOLDER = Path(env("OUTBOX_FOLDER", default="_outbox"))


@app.command()
def main():
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
    app()
