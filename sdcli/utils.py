from contextlib import contextmanager
from pathlib import Path

import typer
from cachecontrol import CacheControl

from .tattling_session import TattlingSession


def _get_creds():
    output = Path.home() / ".sdcli" / "credentials"

    try:
        gh_user, gh_password = output.read_text().split("\n")
        return gh_user, gh_password
    except Exception:
        typer.secho(
            "You must login with `sdcli gh auth` first!", fg=typer.colors.BRIGHT_RED
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
        with TattlingSession() as session:
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
