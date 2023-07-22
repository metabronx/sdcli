import hashlib
import os
from contextlib import contextmanager
from pathlib import Path
from subprocess import PIPE, CalledProcessError, run
from typing import List, Optional, Tuple, Union

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
            "\n[ X ] Something went wrong communicating with GitHub.\n",
            fg=typer.colors.BRIGHT_RED,
        )
        raise typer.Exit(code=1)


def run_command(command: Union[str, List[str]], capture: bool = False):
    """
    Run an arbitrary command with arbitrary arguments and return the CompletedProcess.
    STDERR is captured and formatted upon unsuccessful command execution, either at the
    command or OS level. If capture is True, STDOUT is captured.
    """
    if isinstance(command, str):
        command = command.split(" ")

    try:
        # try to the provided command as a subprocess, capturing
        # the stderr if the command fails
        return run(
            command,
            text=True,
            stdout=(capture and PIPE) or None,
            stderr=PIPE,
            check=True,
        )
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
                " ignore the rest.\n      Otherwise, the traceback from"
                f" `{' '.join(command)}` was recaptured and is printed.",
                fg=typer.colors.BRIGHT_RED,
            )
            + errmsg
        )
        raise typer.Exit(code=1)


def is_docker_supported():
    """Checks if Docker and Docker Compose 2 exist on the system and are running."""
    try:
        run_command("docker version", capture=True)
        docker_check = run_command("docker compose version", capture=True)
    except (CalledProcessError, FileNotFoundError):
        docker_check = None

    if not docker_check or docker_check.returncode != 0:
        typer.secho(
            "[ X ] Docker Compose V2 is not available but is required. Ensure Docker is"
            " running and Docker Compose V2 is installed before continuing.",
            fg=typer.colors.BRIGHT_RED,
        )
        raise typer.Exit(code=1)


def fingerprint_path(
    *service: str,
    fingerprint: Optional[str] = None,
    hashable: Tuple[Optional[str]] = (),
) -> Tuple[str, Path]:
    """
    Returns the cache path for a given fingerprint or hashable under the provided
    service.
    """
    any_hashable = any(hashable)
    if (not fingerprint and not any_hashable) or (fingerprint and any_hashable):
        typer.secho(
            "[ X ] You must supply either the fingerprint of an already configured"
            " service or a complete unique identifier for a new fingerprint.",
            fg=typer.colors.BRIGHT_RED,
        )
        raise typer.Exit(code=1)
    elif any_hashable and not all(hashable):
        typer.secho(
            "[ X ] It doesn't seem like you've provided all the arguments required to"
            " produce a unique fingerprint. Check your specific command usage.",
            fg=typer.colors.BRIGHT_RED,
        )
        raise typer.Exit(code=1)

    det_fingerprint = (
        fingerprint
        # we need predictable results between interpreters, which hash() won't provide
        or hashlib.md5("|".join(hashable).encode(), usedforsecurity=False).hexdigest()
    )

    path = Path.home().joinpath(
        ".sdcli",
        *service,
        det_fingerprint,
    )

    if fingerprint and not path.exists():
        typer.secho(
            f"[ X ] The provided fingerprint '{det_fingerprint}' does not exist.",
            fg=typer.colors.BRIGHT_RED,
        )
        raise typer.Exit(code=1)

    return det_fingerprint, path
