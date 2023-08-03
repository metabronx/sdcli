"""
Tests all the GitHub suite commands. Requests and responses are mocked (imitated) so
that nothing is actually sent over the wire. Everything is also run, via the
'filesystem' autoused fixture, in an isolated filesystem that is deleted and recreated
after / before each test.
"""
from pathlib import Path


def test_login(invoke_command, filesystem):
    """Test the login command. It should write the given credentials to file."""
    credentials = filesystem / ".sdcli" / "credentials"

    assert not credentials.exists()
    res = invoke_command("gh login", input="username\npassword")

    assert res.exit_code == 0
    assert credentials.exists()
    assert credentials.read_text() == "username\npassword"


def test_invite_single(requests_mock, invoke_command):
    """Test invocation for inviting a single email to the org."""
    # mocked github requests
    requests_mock.get(
        "https://api.github.com/orgs/metabronx/teams",
        json=[{"id": 1, "slug": "abba"}, {"id": 2, "slug": "queen"}],
    )
    requests_mock.post("https://api.github.com/orgs/metabronx/invitations")

    res = invoke_command(
        "gh invite test.user@metabronx.com --team abba --team queen",
        env={"GH_USERNAME": "test.user", "GH_TOKEN": "password"},
    )
    assert res.exit_code == 0

    # one for the team call, one for the invite
    assert requests_mock.call_count == 2

    req = requests_mock.last_request
    assert req.method == "POST"
    assert req.url == "https://api.github.com/orgs/metabronx/invitations"
    assert req.json() == {
        "email": "test.user@metabronx.com",
        "role": "direct_member",
        "team_ids": [1, 2],
    }


def test_invite_from_file(requests_mock, invoke_command):
    """Test the invocation for inviting multiple emails via CSV."""
    requests_mock.get(
        "https://api.github.com/orgs/metabronx/teams",
        json=[{"id": 1, "slug": "abba"}, {"id": 2, "slug": "queen"}],
    )
    requests_mock.post("https://api.github.com/orgs/metabronx/invitations")

    # mocked csv
    Path("mock_accounts.csv").write_text(
        "test.user0@metabronx.com\ntest.user1@metabronx.com"
    )

    res = invoke_command(
        "gh invite --from-file mock_accounts.csv --team abba --team queen",
        env={"GH_USERNAME": "test.user", "GH_TOKEN": "password"},
    )
    assert res.exit_code == 0

    # one for the team call, 1 for each invite
    assert requests_mock.call_count == 3

    for i, req in enumerate(requests_mock.request_history[1:]):
        assert req.method == "POST"
        assert req.url == "https://api.github.com/orgs/metabronx/invitations"
        assert req.json() == {
            "email": f"test.user{i}@metabronx.com",
            "role": "direct_member",
            "team_ids": [1, 2],
        }


def test_assign_teams(requests_mock, invoke_command):
    """Test the invocation for assigning multiple users to different teams via CSV."""
    assignments = [("test.user0", "members"), ("test.user1", "engineers")]

    for u, t in assignments:
        requests_mock.put(
            f"https://api.github.com/orgs/metabronx/teams/{t}/memberships/{u}"
        )

    Path("mock_assignments.csv").write_text(
        "\n".join(f"{u},{t}" for u, t in assignments)
    )

    res = invoke_command(
        "gh assign-teams mock_assignments.csv",
        env={"GH_USERNAME": "test.user", "GH_TOKEN": "password"},
    )
    assert res.exit_code == 0

    # one for each assignment
    assert requests_mock.call_count == len(assignments)

    for (u, t), req in zip(assignments, requests_mock.request_history):
        assert req.method == "PUT"
        assert (
            req.url
            == f"https://api.github.com/orgs/metabronx/teams/{t}/memberships/{u}"
        )
        assert req.json() == {"role": "member"}


def test_remove_single(requests_mock, invoke_command):
    """Test the invocation for removing a single user from the org."""
    requests_mock.delete("https://api.github.com/orgs/metabronx/members/test.user")

    invoke_command(
        "gh remove test.user", env={"GH_USERNAME": "test.user", "GH_TOKEN": "password"}
    )

    # one for the deletion
    assert requests_mock.call_count == 1

    req = requests_mock.last_request
    assert req.method == "DELETE"
    assert req.url == "https://api.github.com/orgs/metabronx/members/test.user"


def test_remove_from_file(requests_mock, invoke_command):
    """Test the invocation for removing multiple users from the org via CSV."""
    users = ["test.user0", "test.user1"]

    for username in users:
        requests_mock.delete(
            f"https://api.github.com/orgs/metabronx/members/{username}"
        )

    Path("mock_removals.csv").write_text("\n".join(users))

    res = invoke_command(
        "gh remove --from-file mock_removals.csv",
        env={"GH_USERNAME": "test.user", "GH_TOKEN": "password"},
    )
    assert res.exit_code == 0

    # one for each assignment
    assert requests_mock.call_count == len(users)

    for u, req in zip(users, requests_mock.request_history):
        assert req.method == "DELETE"
        assert req.url == f"https://api.github.com/orgs/metabronx/members/{u}"
