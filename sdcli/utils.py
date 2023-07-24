import hashlib
import os
import shutil
from contextlib import contextmanager
from pathlib import Path
from subprocess import PIPE, CalledProcessError, CompletedProcess, run
from typing import Iterator, List, Optional, Tuple, Union, cast

import typer
from cachecontrol import CacheControl

from .retry_session import RetrySession


def _get_creds() -> Tuple[str, str]:
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
def wrap_ghsession() -> Iterator[RetrySession]:
    """
    Wraps the function within an GH authenticated requests session. Useful for doing
    tons of sequential api calls.
    """
    gh_user, gh_pat = _get_creds()

    try:
        # create a session that is already authenticated and has the headers
        # required by the GitHub REST API.
        with RetrySession() as session:
            cc_session: RetrySession = cast(RetrySession, CacheControl(session))
            cc_session.headers = {
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "sdcli",
            }
            cc_session.auth = (gh_user, gh_pat)
            yield cc_session
    except Exception:
        typer.secho(
            "\n[ X ] Something went wrong communicating with GitHub.\n",
            fg=typer.colors.BRIGHT_RED,
        )
        raise typer.Exit(code=1)


def run_command(
    command: Union[str, List[str]], capture: bool = False, exit_on_error: bool = True
) -> Optional[CompletedProcess[str]]:
    """
    Run an arbitrary command with arbitrary arguments and return the CompletedProcess.
    STDERR is captured and formatted upon unsuccessful command execution, either at the
    command or OS level. If capture is True, STDOUT is captured.
    """
    if isinstance(command, str):
        command = command.split(" ")

    process: Optional[CompletedProcess[str]] = None
    try:
        # try to the provided command as a subprocess, capturing
        # the stderr if the command fails
        process = run(
            command,
            text=True,
            stdout=(capture and PIPE) or None,
            stderr=PIPE,
            check=True,
        )
    except Exception as err:
        if not exit_on_error:
            raise err

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
    else:
        return process


def is_docker_supported() -> None:
    """Checks if Docker and Docker Compose exist on the system and are running."""
    try:
        run_command("docker version", capture=True, exit_on_error=False)
        docker_check = run_command(
            "docker-compose --version", capture=True, exit_on_error=False
        )
    except (CalledProcessError, FileNotFoundError):
        docker_check = None

    if not docker_check or docker_check.returncode != 0:
        typer.secho(
            "[ X ] Docker Compose is not available but is required. Ensure Docker is"
            " running and Docker Compose is installed before continuing.\n      For"
            " compatibility, sdcli assumes the `docker-compose` command is available.",
            fg=typer.colors.BRIGHT_RED,
        )
        raise typer.Exit(code=1)


def validate_compose_yaml(yaml: Union[str, Path], fingerprint_path: Path) -> None:
    """
    Checks if the provided yaml is valid for the installed version of Docker Compose.
    """
    try:
        run_command(
            f"docker-compose -f {yaml} config -o {yaml}",
            capture=True,
            exit_on_error=False,
        )
    except CalledProcessError:
        fingerprint = fingerprint_path.stem
        shutil.rmtree(fingerprint_path)
        typer.secho(
            f"[ X ] The services configuration file with fingerprint '{fingerprint}' is"
            " not compatible with your version of Docker Compose. Please upgrade your"
            " Docker and Docker Compose versions, then try again.",
            fg=typer.colors.BRIGHT_RED,
        )
        raise typer.Exit(code=1)


def fingerprint_path(
    *service: str,
    fingerprint: Optional[str] = None,
    hashable: Tuple[Optional[str], ...] = (),
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
        or hashlib.md5(
            "|".join(cast(Tuple[str, ...], hashable)).encode(), usedforsecurity=False
        ).hexdigest()
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
