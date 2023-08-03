"""Tests utilities used by the CLI."""
import platform
from contextlib import nullcontext, suppress
from pathlib import Path
from subprocess import CalledProcessError
from unittest.mock import MagicMock

import pytest
from typer import Exit as ExitError

from sdcli.utils import (
    _get_hashlib_kwargs,
    fingerprint_path,
    is_container_running,
    is_docker_supported,
    run_command,
    validate_compose_yaml,
    wrap_ghsession,
)

PYTHON_VERSION = f"Python {platform.python_version()}"


@pytest.mark.parametrize("version", [(3, 7), (3, 9)])
def test_hashlib_kwargs(monkeypatch, version):
    """
    Checks that the `usedforsecurity` kwarg to hashlib is only present on compatible
    Python versions (3.9+).
    """
    monkeypatch.setattr("sys.version_info", version)

    kwargs = _get_hashlib_kwargs()
    _get_hashlib_kwargs.cache_clear()

    if version[1] == 7:
        assert "usedforsecurity" not in kwargs
    else:
        assert kwargs["usedforsecurity"] is False


def test_wrap_ghsession_no_auth(capfd):
    """Checks that GitHub request sessions error properly if unauthenticated."""
    with pytest.raises(ExitError):
        with wrap_ghsession():
            pass

    assert "You must login" in capfd.readouterr().out


def test_wrap_ghsession_bad_auth_env_vars(monkeypatch, requests_mock, capfd):
    """
    Checks that GitHub request sessions error properly if using bad environment
    credentials.
    """
    monkeypatch.setenv("GH_USERNAME", "username")
    monkeypatch.setenv("GH_TOKEN", "token")

    with pytest.raises(ExitError):
        with wrap_ghsession() as session:
            session.get("https://example.com")

    assert "Something went wrong communicating with GitHub." in capfd.readouterr().out


def test_wrap_ghsession_bad_auth_file(monkeypatch, requests_mock, filesystem, capfd):
    """
    Checks that GitHub request sessions error properly if using bad cached file
    credentials.
    """
    creds = filesystem / ".sdcli" / "credentials"
    creds.parent.mkdir()
    creds.write_text("username\ntoken")

    with pytest.raises(ExitError):
        with wrap_ghsession() as session:
            session.get("https://example.com")

    assert "Something went wrong communicating with GitHub." in capfd.readouterr().out


@pytest.mark.parametrize(
    "command,kwargs,exception",
    [
        (["python", "--version"], {}, None),
        ("python --version", {}, None),
        ("python --version", {"capture": True}, None),
        ("notfound", {}, pytest.raises(ExitError)),
        ("notfound", {"exit_on_error": False}, pytest.raises(FileNotFoundError)),
        ("python --invalid", {}, pytest.raises(ExitError)),
        (
            "python --invalid",
            {"exit_on_error": False},
            pytest.raises(CalledProcessError),
        ),
    ],
)
def test_run_command(command, kwargs, exception, capfd):
    """
    Check that `run_command` works as when provided with different types of commands
    and different configurations. `exit_on_error` captures errors and wraps them nicely,
    or propagates them back upwards. `capture` optionally pipes stout to the parent
    process.
    """
    with exception or nullcontext():
        process = run_command(command, **kwargs)
        captured = capfd.readouterr()

        assert (
            (kwargs.get("capture", False) and process.stdout) or captured.out
        ).strip() == PYTHON_VERSION

        if not process and kwargs.get("exit_on_error", True):
            assert captured.err.startswith("\n[ X ]")


def test_is_docker_supported(mock_run_command):
    """
    Checks that the docker support callback calls the proper commands.
    """
    is_docker_supported()

    mock_run_command.assert_any_call(
        "docker version", capture=True, exit_on_error=False
    )
    mock_run_command.assert_any_call(
        "docker-compose --version", capture=True, exit_on_error=False
    )


@pytest.mark.parametrize(
    "error",
    [
        CalledProcessError(returncode=1, cmd=["mock"]),
        FileNotFoundError(),
        # this is for when docker exists but version failed due to the engine not
        # running. we check if `.returncode == 0`, which it won't here since the mock
        # attribute will also be a mock.
        MagicMock(),
    ],
)
def test_is_docker_supported_no(mock_run_command, error):
    """
    Checks the docker support callback errors gracefully if docker isn't installed or
    the engine isn't running.
    """
    mock_run_command.side_effect = error

    with pytest.raises(ExitError):
        is_docker_supported()

    mock_run_command.assert_any_call(
        "docker version", capture=True, exit_on_error=False
    )

    if isinstance(error, MagicMock):
        mock_run_command.assert_any_call(
            "docker-compose --version", capture=True, exit_on_error=False
        )


@pytest.mark.parametrize(
    "fingerprint,hashable,exce_msg",
    [
        # hashable
        (None, ("param1", "param2"), None),
        # fingerprint
        ("7e1175602988b19bdca7a75619d5563f", (None, None), None),
        # both, invalid
        ("7e1175602988b19bdca7a75619d5563f", ("param1", "param2"), "You must supply"),
        # neither, invalid
        (None, (None, None), "You must supply"),
        # incomplete hashable
        (None, ("param1", None), "It doesn't seem"),
        # bad fingerprint
        ("bad-fingerprint", (None, None), "The provided fingerprint"),
    ],
)
def test_fingerprint_path(fingerprint, hashable, exce_msg, capfd):
    """
    Check if `fingerprint_path` properly checks edge cases, and returns a proper
    fingerprint when provided with one or a complete hashable.
    """
    det_fingerprint = "7e1175602988b19bdca7a75619d5563f"

    Path(det_fingerprint).mkdir()

    with suppress(ExitError):
        fp, _ = fingerprint_path("test", fingerprint=fingerprint, hashable=hashable)
        assert fp == det_fingerprint

    if exce_msg:
        assert exce_msg in capfd.readouterr().out


def test_validate_compose_yaml(mock_run_command, filesystem):
    """Checks that compose validation actually triggers compose yaml normalization."""
    yaml = filesystem / "docker-compose.yaml"
    str_yaml = str(yaml)

    validate_compose_yaml(yaml, filesystem)

    mock_run_command.assert_called_once_with(
        ["docker-compose", "-f", str_yaml, "config", "-o", str_yaml],
        capture=True,
        exit_on_error=False,
    )


def test_validate_compose_yaml_fail(mock_run_command, filesystem, capfd):
    """
    Checks that failed compose validation prints the proper error, renames the failed
    file, and logs the command and output.
    """

    yaml = filesystem / "docker-compose.yaml"
    yaml.touch()
    str_yaml = str(yaml)

    mock_run_command.side_effect = CalledProcessError(
        cmd=["validate-yaml"], returncode=1, stderr="mock err"
    )

    with pytest.raises(ExitError):
        validate_compose_yaml(yaml, filesystem)

    mock_run_command.assert_called_once_with(
        ["docker-compose", "-f", str_yaml, "config", "-o", str_yaml],
        capture=True,
        exit_on_error=False,
    )

    assert "could not be validated" in capfd.readouterr().out
    assert yaml.with_name("docker-compose.yaml.invalid").exists()
    assert (
        yaml.with_name("validation.log").read_text() == "==> validate-yaml\n\nmock err"
    )


def test_is_container_running(mock_run_command):
    """Checks that the containing running function calls the expected command."""
    mock_run_command.return_value.stdout = ""

    assert not is_container_running("banana")
    mock_run_command.assert_called_once_with(
        'docker ps --format "{{.Names}}"', capture=True
    )
