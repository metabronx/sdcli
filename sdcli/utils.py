import os
from contextlib import contextmanager
from pathlib import Path

import typer
from cachecontrol import CacheControl

from .retry_session import RetrySession


def _get_creds():
    # try to read credentials from environment variables
    gh_user, gh_password = os.environ.get("GH_USERNAME"), os.environ.get("GH_TOKEN")
    if gh_user and gh_password:
        return gh_user, gh_password
    else:
        # if envars aren't specified, try to read credentials from file
        try:
            output = Path.home() / ".sdcli" / "credentials"
            gh_user, gh_password = output.read_text().split("\n")
            return gh_user, gh_password
        except Exception:
            typer.secho(
                "You must login with `sdcli gh auth` first, or supply your username and"
                " personal access token via the GH_USERNAME and GH_TOKEN environment"
                " variables!",
                fg=typer.colors.BRIGHT_RED,
            )
            raise typer.Exit(code=1)


@contextmanager
def wrap_ghsession():
    """
    Wraps the function within an GH authenticated requests session. Useful for doing
    tons of sequential api calls.
    """
    gh_user, gh_pat = _get_creds()

    try:
        # create a session that is already authenticated and has the headers
        # required by the GitHub REST API.
        with RetrySession() as session:
            session = CacheControl(session)
            session.headers = {
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "sdcli",
            }
            session.auth = (gh_user, gh_pat)
            yield session
    except Exception:
        typer.secho(
            "\n[ X ] Something went wrong. Here is the traceback:\n",
            fg=typer.colors.BRIGHT_RED,
        )
        raise
