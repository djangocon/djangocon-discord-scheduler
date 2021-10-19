import datetime
import frontmatter
import pytz
import typer

from dateutil.parser import parse
from environs import Env
from pathlib import Path


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
