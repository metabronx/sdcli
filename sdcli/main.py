import typer

from .blackstrap import s3_typer as blackstrap_s3
from .commands import gh

app = typer.Typer(
    help="A command-line utility for executing essential and / or laborious tasks.",
    no_args_is_help=True,
)

# subcommands
app.add_typer(
    gh, name="gh", help="Does things with GitHub's v3 REST API.", no_args_is_help=True
)
app.add_typer(
    blackstrap_s3,
    name="s3",
    help="Does things with Amazon AWS S3.",
    no_args_is_help=True,
)
