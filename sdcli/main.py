import csv
from pathlib import Path
from typing import List, Optional

import typer
from tqdm import tqdm

from .utils import wrap_ghsession

app = typer.Typer(
    help="A command-line utility for executing essential but laborious tasks.",
    add_completion=False,
)
gh_app = typer.Typer()
app.add_typer(gh_app, name="gh", help="Does things with GitHub's v3 REST API.")


@gh_app.command("auth")
def gh_login():
    """
    Authenticates your machine with GitHub so any future requests are executed as
    yourself. To avoid saving your credentials on your host machine, you may export
    the GH_USERNAME and GH_TOKEN environment variable or pass them to every command.

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
    team: Optional[List[str]] = typer.Option(
        None,
        help="The organization teams to which to invite the person(s). Pass this option"
        " multiple times to include more than one team. Defaults to 'members'.",
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
    Invited users are automatically added to the "members" team, unless other options
    are given.
    """
    # check that an email was provided xor a list of emails
    if (not email and not from_file) or (email and from_file):
        typer.secho(
            "[ X ] You must supply either an email or file of emails.",
            fg=typer.colors.BRIGHT_RED,
        )
        raise typer.Exit(code=1)

    # invite all members
    with wrap_ghsession() as session:
        team_ids = []
        team = team or ["members"]
        # fetch team IDs to pass to through during user invitation. it's easier
        # (and faster) to fetch ALL our organization teams and then to filter them,
        # rather than fetching each concurrently.
        if team:
            resp = session.get(
                "https://api.github.com/orgs/metabronx/teams",
                params={"per_page": 100},
            )
            team_ids = [t["id"] for t in resp.json() if t["slug"] in team]

        def _invite(email: str):
            # create an invitation for the specified email with a default "member"
            # role in the organization and, if supplied, teams.
            session.post(
                "https://api.github.com/orgs/metabronx/invitations",
                json={
                    "email": email,
                    "role": "direct_member",
                    "team_ids": team_ids,
                },
            )

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
            # create a progress bar for visual kindness and run through creating
            # all the invitations
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
        help="A csv text file of usernames and team memberships, without a header.",
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
            session.put(
                "https://api.github.com"
                f"/orgs/metabronx/teams/{team}/memberships/{username}",
                json={
                    "role": "member",
                },
            )

        # read and submit all the team assignments
        assignments = [(ts[0], ts[1]) for ts in teamships]
        # do all the team assignments in parallel
        typer.echo()
        for user, slug in tqdm(
            assignments,
            desc="Assigning teamships for all the provided users",
            bar_format="{l_bar}{bar}",
        ):
            _assign(user.strip(), slug.strip())

        unique_teams = len({t for _, t in assignments})
        typer.secho(
            f"[ ✔ ] Successfully assigned {len(assignments)} user(s) to"
            f" {unique_teams} different team(s).\n",
            fg=typer.colors.GREEN,
        )


@gh_app.command("remove")
def gh_remove(
    username: Optional[str] = typer.Argument(
        None,
        help="The username of the person to remove. This option is mutually exclusive"
        " with `--from-file`.",
    ),
    from_file: Optional[typer.FileText] = typer.Option(
        None,
        help="A line-delimited text file of usernames to remove. This option "
        "is mutually exclusive with supplying a single username.",
    ),
):
    """
    Removes the given username or list of usernames from the metabronx GitHub
    organization. A list of usernames must be a text file, where each username is on a
    separate line.
    """
    # check that an email was provided xor a list of emails
    if (not username and not from_file) or (username and from_file):
        typer.secho(
            "[ X ] You must supply either a username or file of usernames.",
            fg=typer.colors.BRIGHT_RED,
        )
        raise typer.Exit(code=1)

    # invite all members
    with wrap_ghsession() as session:

        def _remove(username: str):
            # remove the specified username from the organization, or cancel a pending
            # invitation. this will send an email notification.
            session.delete(f"https://api.github.com/orgs/metabronx/members/{username}")

        count = 0
        if username:
            # remove a single person if a username was supplied
            _remove(username)
            count = 1
        elif from_file:
            # if a file was supplied, get all the users from it and strip away
            # any whitespace
            users = [user.strip() for user in from_file]
            count = len(users)
            # remove all the users
            typer.echo()
            for user in tqdm(
                users,
                desc="Removing all members in the given file",
                bar_format="{l_bar}{bar}",
            ):
                _remove(user)

        typer.secho(
            f"\n[ ✔ ] Successfully removed {count} person(s) from metabronx.",
            fg=typer.colors.GREEN,
        )
