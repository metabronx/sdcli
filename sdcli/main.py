import csv
import time
from pathlib import Path
from typing import List, Optional

import typer
from tqdm import tqdm

from .utils import wrap_ghsession

app = typer.Typer(add_completion=False)
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

    # invite all members
    with wrap_ghsession() as session:
        team_ids = []
        # if team slugs were provided, fetch their IDs to pass to through during
        # user invitation. it's easier (and faster) to fetch ALL our organization
        # teams and then to filter them, rather than fetching each concurrently.
        if team_slugs:
            resp = session.get(
                "https://api.github.com/orgs/metabronx/teams",
                params={"per_page": 100},
            )
            resp.raise_for_status()
            team_ids = [
                team["id"] for team in resp.json() if team["slug"] in team_slugs
            ]

        def _invite(email: str):
            # create an invitation for the specified email with a default "member"
            # role in the organization and, if supplied, teams.
            resp = session.post(
                "https://api.github.com/orgs/metabronx/invitations",
                json={
                    "email": email,
                    "role": "direct_member",
                    "team_ids": team_ids,
                },
            )
            # GitHub may rate limit us, in which case we need to wait
            # the amount of time they tell us before retrying
            retry = resp.headers.get("Retry-After")
            if retry:
                time.sleep(retry)
                _invite(email)

        count = 0
        if email:
            # invite a single person if an email was supplied
            _invite(email)
            count = 1
        elif from_file:
            # if a file was supplied, get all the users from it and strip away
            # any whitespace
            users = [user.strip() for user in from_file]
            count = len(users)
            # create a progress bar for visual kindness
            #
            # create all the invitation coroutines and put them all into the
            # event loop for concurrent execution
            typer.echo()
            for user in tqdm(
                users,
                desc="Inviting all members in the given file",
                bar_format="{l_bar}{bar}",
            ):
                _invite(user)

        typer.secho(
            f"\n[ ✔ ] Successfully invited {count} person(s) to metabronx.",
            fg=typer.colors.GREEN,
        )


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

    # assign all teamships
    with wrap_ghsession() as session:

        def _assign(username: str, team: str):
            # assign the specified user to the given team as a member
            resp = session.put(
                "https://api.github.com"
                f"/orgs/metabronx/teams/{team}/memberships/{username}",
                json={
                    "org": "metabronx",
                    "team_slug": team,
                    "username": username,
                    "role": "member",
                },
            )
            # GitHub may rate limit us, in which case we need to wait
            # the amount of time they tell us before retrying
            retry = resp.headers.get("Retry-After")
            if retry:
                time.sleep(retry)
                _assign(username, team)

        # read and submit all the team assignments
        assignments = [(ts[0], ts[1]) for ts in teamships]
        # do all the team assignments in parallel
        typer.echo()
        for user, slug in tqdm(
            assignments,
            desc="Assigning teamships for all the provided users",
            bar_format="{l_bar}{bar}",
        ):
            _assign(user, slug)

        unique_teams = len({t for _, t in assignments})
        typer.secho(
            f"[ ✔ ] Successfully assigned {len(assignments)} user(s) to"
            f" {unique_teams} different team(s).\n",
            fg=typer.colors.GREEN,
        )
