import asyncio
from pathlib import Path
from typing import List, Optional

import aiohttp
import typer

app = typer.Typer()
gh_app = typer.Typer()
app.add_typer(gh_app, name="gh", help="Does things with GitHub's v3 REST API.")


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


@app.callback()
def callback():
    """
    A command-line utility for executing essential but laborious tasks.
    """


@gh_app.command("auth")
def gh_login():
    """
    Authenticates your machine with GitHub so any future requests are executed as
    yourself. To avoid saving your credentials on your host machine, you may set an
    environment variable or pass them to every command.

    Credentials are stored in plain-text at `~/.sdcli/credentials`.
    """
    typer.secho(
        "\n[ ! ] Warning! This will save your GitHub credentials locally to perform all"
        " future `gh` commands. Anything saved already will be overwritten.\n",
        fg=typer.colors.BRIGHT_RED,
    )

    # prompt for username and PAT
    username = typer.prompt("  Username")
    personal_access_token = typer.prompt("  Personal access token")

    # write the credentials to a cache directory in the user's home directory
    output = Path.home() / ".sdcli" / "credentials"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(f"{username}\n{personal_access_token}")

    typer.secho(
        "\n[ ✔ ] Credentials written to '~/.sdcli/credentials' successfully",
        fg=typer.colors.GREEN,
    )


@gh_app.command("invite")
def gh_invite(
    email: Optional[str] = typer.Argument(
        None,
        help="The email address of the person to invite. This option is mutually"
        " exclusive with `--from-file`.",
    ),
    team_slugs: Optional[List[str]] = typer.Option(
        None, help="The organization teams to which to invite the person(s)."
    ),
    from_file: Optional[typer.FileText] = typer.Option(
        None,
        help="A line-delimited text file of email address to invite. This option "
        "is mutually exclusive with supplying a single email address.",
    ),
):
    """
    Invites the given email or list of emails to the sdbase GitHub organization. A list
    of emails must be a UTF-8 text file, where each email is on a separate line.
    """
    # get credentials, throwing an error if they're not there
    gh_user, gh_pat = _get_creds()
    if (not email and not from_file) or (email and from_file):
        typer.secho(
            "[ X ] You must supply either an email or file of emails.",
            fg=typer.colors.BRIGHT_RED,
        )
        raise typer.Exit()

    # we use aiohttp to do tons of concurrent invites, so everything needs to be within
    # an asyncio coroutine to execute in an event loop.
    async def _inner():
        # create an aiohttp session that is already authenticated and has the headers
        # required by the GitHub REST API.
        async with aiohttp.ClientSession(
            raise_for_status=True,
            headers={"Accept": "application/vnd.github.v3+json", "User-Agent": "sdcli"},
            auth=aiohttp.BasicAuth(login=gh_user, password=gh_pat),
        ) as session:
            team_ids = []
            # if team slugs were provided, fetch their IDs to pass to through during
            # user invitation. it's easier (and faster) to fetch ALL our organization
            # teams and then to filter them, rather than fetching each concurrently.
            if team_slugs:
                async with session.get(
                    "https://api.github.com/orgs/sdbase/teams",
                    params={"per_page": 100},
                ) as resp:
                    data = await resp.json()
                    team_ids = [
                        team["id"] for team in data if team["slug"] in team_slugs
                    ]

            async def _invite(email: str, progressbar=None):
                # create an invitation for the specified email with a default "member"
                # role in the organization and, if supplied, teams.
                async with session.post(
                    "https://api.github.com/orgs/sdbase/invitations",
                    json={
                        "email": email,
                        "role": "direct_member",
                        "team_ids": team_ids,
                    },
                ) as resp:
                    # GitHub may rate limit us, in which case we need to wait
                    # the amount of time they tell us before retrying
                    retry = resp.headers.get("Retry-After")
                    if retry:
                        await asyncio.sleep(retry)
                        await _invite(email)
                    elif progressbar:
                        # update the progress bar if we have one
                        progressbar.update(1)

            count = 0
            if email:
                # invite a single person if an email was supplied
                await _invite(email)
                count = 1
            elif from_file:
                # if a file was supplied, get all the users from it and strip away
                # any whitespace
                users = [user.strip() for user in from_file]
                count = len(users)
                typer.echo()
                # create a progress bar for visual kindness
                with typer.progressbar(
                    length=count, label="Inviting all members in the given file"
                ) as progress:
                    # create all the invitation coroutines and put them all into the
                    # event loop for concurrent execution
                    await asyncio.gather(
                        *[_invite(user, progressbar=progress) for user in users]
                    )

            typer.secho(
                f"\n[ ✔ ] Successfully invited {count} person(s) to sdbase.",
                fg=typer.colors.GREEN,
            )

    # create an event loop and call the inner coroutine, waiting for it to finish
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(_inner())
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
