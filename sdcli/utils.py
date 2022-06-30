from pathlib import Path
import typer
import asyncio
import aiohttp


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


async def with_ghsession(_inner, *args, **kwargs):
    """
    Wraps the function within an GH authenticated aiohttp session. Useful for doing
    tons of concurrent api calls. Must be used with `run_async` to be scheduled within
    an event loop.
    """
    gh_user, gh_pat = _get_creds()

    # create an aiohttp session that is already authenticated and has the headers
    # required by the GitHub REST API.
    async with aiohttp.ClientSession(
        raise_for_status=True,
        headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "sdcli"},
        auth=aiohttp.BasicAuth(login=gh_user, password=gh_pat),
    ) as session:
        return _inner(session=session, *args, **kwargs)


def run_async(_coroutine):
    """
    Creates an event loop and runs the inner coroutine, waiting for it to finish.
    """
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(_coroutine)
    except Exception:
        typer.secho(
            "\n[ X ] Something went wrong somewhere. Here is the traceback:\n",
            fg=typer.colors.BRIGHT_RED,
        )
        raise
    finally:
        pass
        # for some reason, the loop is closed already? not clear
        # loop.close()
