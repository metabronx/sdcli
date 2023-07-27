"""Tests utilities used by the CLI."""
import platform
from contextlib import nullcontext, suppress
from pathlib import Path
from subprocess import CalledProcessError

import pytest
from typer import Exit as ExitError

from sdcli.utils import (
    fingerprint_path,
    run_command,
)

PYTHON_VERSION = f"Python {platform.python_version()}"


@pytest.mark.parametrize(
    "command,kwargs,exception",
    [
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
