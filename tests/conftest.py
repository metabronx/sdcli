from pathlib import Path

import pytest
from typer.testing import CliRunner

from sdcli.main import app


@pytest.fixture(scope="session")
def runner():
    yield CliRunner()


@pytest.fixture(autouse=True)
def filesystem(runner, monkeypatch):
    with runner.isolated_filesystem() as fs:
        # also change Path.home() to return the isolated fs
        monkeypatch.setattr("pathlib.Path.home", lambda: Path(fs))

        yield fs


@pytest.fixture
def invoke_command(monkeypatch, runner):
    # need to mock the auth env vars for gh
    monkeypatch.setenv("GH_USERNAME", "test.user")
    monkeypatch.setenv("GH_TOKEN", "password")

    def _run(cmd: str, **kwargs):
        return runner.invoke(app, cmd.split(), **kwargs)

    yield _run
