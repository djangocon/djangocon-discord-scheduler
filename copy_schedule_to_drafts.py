"""Iterate through our talks and announce them to discord when it's time to go see the talk.

TODO:
1. Decide how we want to do the actual scheduling: celery? event loop like tornado? cron job?
2. Iterate over all the talks and test it in Discord
3. Delete all the announcements before we invite anyone in
"""
from pathlib import Path
import datetime
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta
from environs import Env
import frontmatter
from jinja2 import Template
import pytz
from slugify import slugify
import typer


CONFERENCE_TZ = pytz.timezone("America/Chicago")
IGNORED_SLUGS = ["desmitificando-el-mantenimiento"]

app = typer.Typer(help="Awesome Announce Talks")
env = Env()

DRAFT_FOLDER = Path(env("DRAFT_FOLDER", default="_drafts"))
INBOX_FOLDER = Path(env("INBOX_FOLDER", default="_inbox"))
OUTBOX_FOLDER = Path(env("OUTBOX_FOLDER", default="_outbox"))


@app.command()
def main(
    talks_path: Path = typer.Argument(
        default="_schedule/talks/", help="Directory where talks are stored"
    )
):
    if not talks_path.exists():
        typer.secho(f"talks-path '{talks_path}' does not exist", fg="red")
        raise typer.Exit()

    if not DRAFT_FOLDER.exists():
        typer.secho(f"DRAFT_FOLDER '{DRAFT_FOLDER}' does not exist", fg="red")
        raise typer.Exit()

    filenames = sorted(list(talks_path.glob("*.md")))
    for filename in filenames:
        try:
            post = frontmatter.loads(filename.read_text())
            new_post = frontmatter.loads("")
            slug = slugify(post["title"])

            if slug not in IGNORED_SLUGS:

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
                new_post["slug"] = slugify(post["title"])
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
                template_filename = Path("templates", f"{post['category']}-preview.html")
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
                    date = new_post["date"]
                    slug = slugify(new_post["title"])
                    talk_filename = "-".join(
                        [
                            f"{date.year:04}",
                            f"{date.month:02}",
                            f"{date.day:02}",
                            f"{date.hour:02}",
                            f"{date.minute:02}",
                            f"{slug}-preview.md",
                        ]
                    )
                    # Hack for timezone formatting changing to "-05:00"
                    new_post["date"] = str(new_post["date"]).replace("-05:00", " -0500")

                    destination = DRAFT_FOLDER.joinpath(talk_filename)
                    # typer.echo(f"copying {filename.name} to {destination.parent}")
                    destination.write_text(frontmatter.dumps(new_post))
                    # rewrite_post = frontmatter.loads(destination.read_text())
                    # destination.write_text(frontmatter.dumps(rewrite_post))

        except Exception as e:
            typer.secho(f"{filename}::{e}", fg="red")


if __name__ == "__main__":
    app()
