from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from sdcli.main import app


class NegativeMagicMock(MagicMock):
    def assert_not_any_call(self, *args, **kwargs):
        """Assert the mock has not been called with the specified arguments."""
        try:
            self.assert_any_call(*args, **kwargs)
            assert False, "call found where it should not have been"
        except AssertionError:
            pass


@pytest.fixture(scope="session")
def runner():
    yield CliRunner()


@pytest.fixture(autouse=True)
def filesystem(runner, monkeypatch):
    with runner.isolated_filesystem() as fs:
        home = Path(fs)

        # also change Path.home() to return the isolated fs
        monkeypatch.setattr("pathlib.Path.home", lambda: home)

        yield home


@pytest.fixture
def invoke_command(runner):
    def _run(cmd: str, **kwargs):
        return runner.invoke(app, cmd.split(), catch_exceptions=False, **kwargs)

    yield _run


@pytest.fixture
def mock_run_command(monkeypatch):
    mock = NegativeMagicMock()
    mock.return_value.returncode = 0
    mock.return_value.stdout = ""
    monkeypatch.setattr("sdcli.utils.run_command", mock)
    yield mock


@pytest.fixture(scope="session")
def truthy_check_docker():
    # monkeypatch isn't session scoped, so use unittest patch instead
    with patch("sdcli.utils.is_docker_supported", new=None):
        yield
