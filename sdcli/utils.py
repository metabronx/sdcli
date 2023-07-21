import os
from contextlib import contextmanager
from pathlib import Path
from subprocess import PIPE, CalledProcessError, run
from typing import Optional, Tuple, Union

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
        raise typer.Exit(code=1)


def run_command(command: Union[str, list]):
    """
    Run an arbitrary command with arbitrary arguments. STDOUT is preserved
    while STDERR is formatted upon unsuccessful command execution, either at
    the command or OS level.
    """
    if isinstance(command, str):
        command = command.split(" ")

    try:
        # try to the provided command as a subprocess, capturing
        # the stderr if the command fails
        run(command, universal_newlines=True, stderr=PIPE, check=True)
    except Exception as err:
        # if the command failed, we only care about its stderr
        if isinstance(err, CalledProcessError):
            err = err.stderr

        errmsg = typer.style(f"\n\n{err}", dim=True) if str(err) else ""

        # the subprocess failed due to an OS exception or an invalid command, so
        # print a nice message instead of throwing a runtime exception
        typer.echo(
            typer.style(
                "\n[ X ] Something went wrong! If you're not a developer,"
                f" ignore the rest. Otherwise, the traceback from `{' '.join(command)}`"
                " was recaptured and is printed.",
                fg=typer.colors.BRIGHT_RED,
            )
            + errmsg
        )
        raise typer.Exit(code=1)


def is_docker_supported():
    """Checks if Docker and Docker Compose 2 exist on the system and are running."""
    try:
        run(["docker", "version"], capture_output=True, check=True)
        docker_check = run(["docker", "compose", "version"], capture_output=True)
    except (CalledProcessError, FileNotFoundError):
        docker_check = None

    if not docker_check or docker_check.returncode != 0:
        typer.secho(
            "[ X ] Docker Compose is not available but is required. Ensure Docker and"
            " Docker Compose 2 are installed and running before continuing.",
            fg=typer.colors.BRIGHT_RED,
        )
        raise typer.Exit(code=1)


def fingerprint_path(
    *service: str,
    fingerprint: Optional[str] = None,
    hashable: Optional[Tuple[str]] = None,
) -> Path:
    """
    Returns the cache path for a given fingerprint or hashable under the provided
    service.
    """
    if (not fingerprint and not hashable) or (fingerprint and hashable):
        typer.secho(
            "[ X ] You must supply either the fingerprint of an already configured"
            " service or a unique identifier for a new fingerprint.",
            fg=typer.colors.BRIGHT_RED,
        )
        raise typer.Exit(code=1)

    path = Path.home().joinpath(".sdcli", *service, fingerprint or str(hash(hashable)))

    if fingerprint and not path.exists():
        typer.secho(
            "[ X ] The fingerprint provided does not exist.", fg=typer.colors.BRIGHT_RED
        )
        raise typer.Exit(code=1)

    return path
