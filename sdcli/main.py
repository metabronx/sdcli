import asyncio
from pathlib import Path
from typing import List, Optional

from aiohttp import ClientSession
from .utils import run_async, with_ghsession
import csv
import typer

app = typer.Typer()
gh_app = typer.Typer()
app.add_typer(gh_app, name="gh", help="Does things with GitHub's v3 REST API.")


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
    Invites the given email or list of emails to the metabronx GitHub organization. A
    list of emails must be a UTF-8 text file, where each email is on a separate line.
    """
    # check that an email was provided xor a list of emails
    if (not email and not from_file) or (email and from_file):
        typer.secho(
            "[ X ] You must supply either an email or file of emails.",
            fg=typer.colors.BRIGHT_RED,
        )
        raise typer.Exit()

    async def _inner(session: ClientSession):
        team_ids = []
        # if team slugs were provided, fetch their IDs to pass to through during
        # user invitation. it's easier (and faster) to fetch ALL our organization
        # teams and then to filter them, rather than fetching each concurrently.
        if team_slugs:
            async with session.get(
                "https://api.github.com/orgs/metabronx/teams",
                params={"per_page": 100},
            ) as resp:
                data = await resp.json()
                team_ids = [team["id"] for team in data if team["slug"] in team_slugs]

        async def _invite(email: str, progressbar=None):
            # create an invitation for the specified email with a default "member"
            # role in the organization and, if supplied, teams.
            async with session.post(
                "https://api.github.com/orgs/metabronx/invitations",
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
            f"\n[ ✔ ] Successfully invited {count} person(s) to metabronx.",
            fg=typer.colors.GREEN,
        )

    # invite all members
    run_async(with_ghsession(_inner))


@gh_app.command("assign-teams")
def assign_teams(
    data: typer.FileText = typer.Argument(
        ...,
        help="A csv text file of usernames and team memberships.",
    ),
):
    """
    Assigns each user to their metabronx GitHub organization team using the
    provided CSV.
    """
    teamships = csv.reader(data, strict=True, skipinitialspace=True)

    async def _inner(session: ClientSession):
        async def _assign(username: str, team: str, progressbar):
            # assign the specified user to the given team as a member
            async with session.post(
                f"https://api.github.com/orgs/teams/{team}/memberships/{username}",
                json={
                    "org": "metabronx",
                    "team_slug": team,
                    "username": username,
                    "role": "member",
                },
            ) as resp:
                # GitHub may rate limit us, in which case we need to wait
                # the amount of time they tell us before retrying
                retry = resp.headers.get("Retry-After")
                if retry:
                    await asyncio.sleep(retry)
                    await _assign(username, team, progressbar)
                else:
                    # update the progress bar
                    await asyncio.sleep(10)
                    progressbar.update(1)

        # read and submit all the team assignments
        assignments = [(ts[0], ts[1]) for ts in teamships]
        with typer.progressbar(
            length=len(assignments),
            label="Assign teamships for all the users in the file.",
        ) as progressbar:
            # do all the team assignments in parallel
            await asyncio.gather(
                *[_assign(user, slug, progressbar) for user, slug in assignments]
            )

    # assign all teamships
    run_async(with_ghsession(_inner))
