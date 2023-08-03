def test_bridge_new(mock_run_command, truthy_check_docker, invoke_command, filesystem):
    """
    Check that providing a new configuration to a bridge results in a new service being
    created and started.
    """
    res = invoke_command(
        "s3 bridge --bucket=test --access-key-id=ID --secret-access-key=KEY"
    )

    assert res.exit_code == 0
    assert b"New bucket information provided." in res.stdout_bytes
    assert b"Connect to your bucket via SFTP" in res.stdout_bytes

    yaml = str(
        filesystem
        / ".sdcli"
        / "blackstrap"
        / "s3"
        / "50da709fdb20cf097cfa452ac2ae13cb"
        / "docker-compose.yaml"
    )

    mock_run_command.assert_any_call(
        ["docker-compose", "-f", yaml, "config", "-o", yaml],
        capture=True,
        exit_on_error=False,
    )
    mock_run_command.assert_any_call(
        ["docker-compose", "-f", yaml, "up", "-d", "--force-recreate"]
    )


def test_bridge_existing_stopped(
    mock_run_command, truthy_check_docker, invoke_command, filesystem
):
    """
    Check that providing an existing configuration to a bridge that isn't running
    results in the service being restarted.
    """
    yaml = (
        filesystem / ".sdcli" / "blackstrap" / "s3" / "banana" / "docker-compose.yaml"
    )
    yaml.parent.mkdir(parents=True)
    yaml.touch(exist_ok=False)

    res = invoke_command("s3 bridge --fingerprint=banana")

    assert res.exit_code == 0
    assert b"Existing S3 bridge configuration found." in res.stdout_bytes
    assert b"Connect to your bucket via SFTP" in res.stdout_bytes
    mock_run_command.assert_any_call('docker ps --format "{{.Names}}"', capture=True)
    mock_run_command.assert_any_call(
        [
            "docker-compose",
            "-f",
            str(yaml),
            "up",
            "-d",
            "--force-recreate",
        ]
    )


def test_bridge_existing_running(
    mock_run_command, truthy_check_docker, invoke_command, filesystem
):
    """
    Check that providing an existing configuration to a bridge that IS running
    results in an error indicating so.
    """
    yaml = (
        filesystem / ".sdcli" / "blackstrap" / "s3" / "banana" / "docker-compose.yaml"
    )
    yaml.parent.mkdir(parents=True)
    yaml.touch(exist_ok=False)

    mock_run_command.return_value.stdout = "banana"
    res = invoke_command("s3 bridge --fingerprint=banana")

    assert res.exit_code == 1
    assert b"Existing S3 bridge configuration found." in res.stdout_bytes
    assert b"Your S3 bridge is already running!" in res.stdout_bytes


def test_bridge_existing_restart(
    mock_run_command, truthy_check_docker, invoke_command, filesystem
):
    """
    Check that providing an existing configuration to a bridge that IS running
    but with the required flag results in the service being restarted.
    """
    yaml = (
        filesystem / ".sdcli" / "blackstrap" / "s3" / "banana" / "docker-compose.yaml"
    )
    yaml.parent.mkdir(parents=True)
    yaml.touch(exist_ok=False)

    mock_run_command.return_value.stdout = "banana"
    res = invoke_command("s3 bridge --fingerprint=banana --force-restart")

    assert res.exit_code == 0
    assert b"Existing S3 bridge configuration found." in res.stdout_bytes
    assert b"Connect to your bucket via SFTP" in res.stdout_bytes
    mock_run_command.assert_not_any_call(
        'docker ps --format "{{.Names}}"', capture=True
    )
    mock_run_command.assert_any_call(
        [
            "docker-compose",
            "-f",
            str(yaml),
            "up",
            "-d",
            "--force-recreate",
        ]
    )


def test_stop_bridge(mock_run_command, truthy_check_docker, invoke_command, filesystem):
    """
    Check that stopping a service that is running results in the service being stopped.
    """
    yaml = (
        filesystem / ".sdcli" / "blackstrap" / "s3" / "banana" / "docker-compose.yaml"
    )
    yaml.parent.mkdir(parents=True)
    yaml.touch(exist_ok=False)

    mock_run_command.return_value.stdout = "banana"
    res = invoke_command("s3 stop-bridge banana")

    assert res.exit_code == 0
    assert b"Shutting down your S3 bridge..." in res.stdout_bytes
    mock_run_command.assert_any_call('docker ps --format "{{.Names}}"', capture=True)
    mock_run_command.assert_any_call(["docker-compose", "-f", str(yaml), "stop"])


def test_stop_bridge_not_running(
    mock_run_command, truthy_check_docker, invoke_command, filesystem
):
    """
    Check that stopping a service that ISN'T running results in an error indicating so.
    """
    yaml = (
        filesystem / ".sdcli" / "blackstrap" / "s3" / "banana" / "docker-compose.yaml"
    )
    yaml.parent.mkdir(parents=True)
    yaml.touch(exist_ok=False)

    mock_run_command.return_value.stdout = ""
    res = invoke_command("s3 stop-bridge banana")

    assert res.exit_code == 1
    assert b"Your S3 bridge is not running." in res.stdout_bytes
    mock_run_command.assert_any_call('docker ps --format "{{.Names}}"', capture=True)


def test_stop_bridge_invalid(
    mock_run_command, truthy_check_docker, invoke_command, filesystem
):
    """
    Check that stopping a service that has a fingerprint path but no compose file
    results in an error indicating so. This is specifically for dealing with either
    explicit user tampering, or something going horribly wrong.
    """
    # note: no compose file, but fingerprint dir
    fp_path = filesystem / ".sdcli" / "blackstrap" / "s3" / "banana"
    fp_path.mkdir(parents=True)

    mock_run_command.return_value.stdout = "banana"
    res = invoke_command("s3 stop-bridge banana")

    assert res.exit_code == 1
    assert (
        b"Your S3 bridge is running, but its underlying configuration file is missing."
        in res.stdout_bytes
    )
    mock_run_command.assert_any_call('docker ps --format "{{.Names}}"', capture=True)


def test_delete_bridge(
    mock_run_command, truthy_check_docker, invoke_command, filesystem
):
    """
    Check that deleting a bridge triggers a compose teardown and deletion of
    all fingerprint path configurations.
    """
    yaml = (
        filesystem / ".sdcli" / "blackstrap" / "s3" / "banana" / "docker-compose.yaml"
    )
    yaml.parent.mkdir(parents=True)
    yaml.touch(exist_ok=False)

    res = invoke_command("s3 delete-bridge banana")

    assert res.exit_code == 0
    assert b"Successfully removed your S3 bridge." in res.stdout_bytes
    mock_run_command.assert_any_call(
        ["docker-compose", "-f", str(yaml), "down", "--volumes"]
    )

    assert not yaml.exists()
    assert not yaml.parent.exists()


def test_delete_bridge_invalid(
    mock_run_command, truthy_check_docker, invoke_command, filesystem
):
    """
    Check that deleting a bridge that doesn't have a compose file doesn't trigger a
    compose teardown (since no file to teardown exists), but still deletes any
    fingerprint path configurations.

    Note: because of the prerequisite fingerprint determination logic, its not possible
    to try and delete a non-existent bridge (missing fingerprint); it will error first.
    """
    fp_path = filesystem / ".sdcli" / "blackstrap" / "s3" / "banana"
    fp_path.mkdir(parents=True)

    res = invoke_command("s3 delete-bridge banana")

    assert res.exit_code == 0
    assert b"Successfully removed your S3 bridge." in res.stdout_bytes
    mock_run_command.assert_not_any_call(
        [
            "docker-compose",
            "-f",
            str(fp_path / "docker-compose.yaml"),
            "down",
            "--volumes",
        ]
    )

    assert not fp_path.exists()
