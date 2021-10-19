import datetime
import frontmatter
import pytz
import typer
import requests

from dateutil.parser import parse
from environs import Env
from pathlib import Path


CONFERENCE_TZ = pytz.timezone("America/Chicago")

app = typer.Typer(help="Awesome Announce Talks")
env = Env()

DISCORD_WEBHOOK = env("DISCORD_WEBHOOK", default=None)
DRAFT_FOLDER = Path(env("DRAFT_FOLDER", default="_drafts"))
INBOX_FOLDER = Path(env("INBOX_FOLDER", default="_inbox"))
OUTBOX_FOLDER = Path(env("OUTBOX_FOLDER", default="_outbox"))


@app.command()
def main(
    post_now: bool = typer.Option(
        default=False,
        help="Pretend the talks are happening now instead of queueing the talks up later "
        "(for testing)",
    )
):
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

    filenames = sorted(list(INBOX_FOLDER.glob("*.md")))
    for filename in filenames:
        post = frontmatter.loads(filename.read_text())
        if isinstance(post["date"], datetime.datetime):
            timestamp = post["date"]
        else:
            timestamp = parse(post["date"])

        timestamp = timestamp.astimezone(CONFERENCE_TZ)
        print(f"timestamp=={timestamp}")
        print(f"now=={now}")
        print(timestamp <= now)
        if timestamp <= now:
            body = {
                "content": post.content,
                "allowed_mentions": {
                    "parse": ["everyone"],
                    "users": [],
                },
            }

            """Post the body to the webhook URL"""
            response = requests.post(DISCORD_WEBHOOK, json=body)
            response.raise_for_status()

            # TODO: fallback into an error folder possibly...

            typer.secho(f"moving {filename.name} to the outbox", fg="green")
            destination = OUTBOX_FOLDER.joinpath(filename.name)
            filename.rename(destination)


if __name__ == "__main__":
    app()
