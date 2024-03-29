import shutil
from pathlib import Path
from string import Template
from typing import Optional

import typer

import sdcli.utils as utils

s3 = typer.Typer(callback=utils.is_docker_supported)


@s3.command("bridge", no_args_is_help=True)
def start_bridge(
    fingerprint: Optional[str] = typer.Option(
        None,
        help="The fingerprint associated with an existing SFTP-bucket bridge. This"
        " option is mutually exclusive with all other options.",
    ),
    bucket: Optional[str] = typer.Option(
        None,
        help="The bucket to expose via SFTP. When you supply this for the first time,"
        " you must also supply access credentials.",
    ),
    access_key_id: Optional[str] = typer.Option(
        None,
        help="Your AWS Access Key ID. This must be supplied when first connecting"
        " to a bucket.",
    ),
    secret_access_key: Optional[str] = typer.Option(
        None,
        help="Your AWS Secret Access Key. This must be supplied when first"
        " connecting to a bucket.",
    ),
    force_restart: bool = typer.Option(
        False,
        "--force-restart",
        help="By default, existing S3 bridges will not be restarted if they're already"
        " running. Specify this flag to override this behavior. This is equivalent to"
        " the `--force-recreate` flag provided Docker Compose.",
    ),
) -> None:
    """Bridges an S3 object store (bucket) to an SFTP-accessible file system."""

    operation = "start"

    det_fingerprint, fp_path = utils.fingerprint_path(
        "blackstrap",
        "s3",
        fingerprint=fingerprint,
        hashable=(bucket, access_key_id, secret_access_key),
    )
    yaml = fp_path / "docker-compose.yaml"
    if not yaml.exists():
        if fingerprint:
            typer.secho(
                "[ X ] The fingerprint provided exists but the underlying bridge"
                " configuration file is missing. This should never happen.\n      "
                "To fix this, please rerun the command providing the bucket, access"
                " key, and secret instead.",
                fg=typer.colors.BRIGHT_RED,
            )
            raise typer.Exit(code=1)

        print("New bucket information provided. Configuring a new bridge...")
        yaml.parent.mkdir(parents=True, exist_ok=True)
        templ_yaml = Path(__file__).with_name("docker-compose.yaml")

        with templ_yaml.open("r") as f:
            template = Template(f.read())
            yaml.write_text(
                template.substitute(
                    {
                        "AWS_S3_BUCKET": bucket,
                        "AWS_S3_ACCESS_KEY_ID": access_key_id,
                        "AWS_S3_SECRET_ACCESS_KEY": secret_access_key,
                        "FINGERPRINT": det_fingerprint,
                    }
                )
            )

        # validate and normalize the generated yaml. this helps catch version mismatches
        # between the template and the locally installed compose version
        utils.validate_compose_yaml(yaml, fp_path)
    else:
        print("Existing S3 bridge configuration found.")
        if not force_restart and utils.is_container_running(det_fingerprint):
            typer.secho(
                "\n[ ! ] Your S3 bridge is already running!\n      If you intended to"
                " force a restart, you must specify the --force-restart option.",
                fg=typer.colors.YELLOW,
            )
            raise typer.Exit(code=1)
        else:
            operation = f"re{operation}"

    print(f"Your S3 bridge is {operation}ing. This may take a few seconds.")
    utils.run_command(
        ["docker-compose", "-f", str(yaml), "up", "-d", "--force-recreate"]
    )

    typer.secho(
        f"\n[ ✔ ] Successfully {operation}ed your S3 bridge!\n      The service has the"
        f" fingerprint '{det_fingerprint}'. You can use it to start this bridge"
        " again without having to provide the same bucket and access credentials.\n"
        "      Connect to your bucket via SFTP at `blackstrap-user@localhost:1111`.",
        fg=typer.colors.GREEN,
    )


@s3.command("stop-bridge", no_args_is_help=True)
def stop_bridge(
    fingerprint: str = typer.Argument(
        ...,
        help="The fingerprint associated with an existing SFTP-bucket bridge.",
    )
) -> None:
    """Shuts down an existing S3 bridge."""
    _, fp_path = utils.fingerprint_path("blackstrap", "s3", fingerprint=fingerprint)
    yaml = fp_path / "docker-compose.yaml"

    if not utils.is_container_running(fingerprint):
        typer.secho("\n[ ! ] Your S3 bridge is not running.", fg=typer.colors.YELLOW)
        raise typer.Exit(code=1)
    elif not yaml.exists():
        typer.secho(
            "\n[ X ] Your S3 bridge is running, but its underlying configuration file"
            " is missing.\n      This should never happen, and usually indicates"
            "mischief. You will have to manually stop your bridge via `docker stop`"
            " instead.",
            fg=typer.colors.BRIGHT_RED,
        )
        raise typer.Exit(code=1)

    print("Shutting down your S3 bridge...")
    utils.run_command(["docker-compose", "-f", str(yaml), "stop"])

    typer.secho(
        "[ ✔ ] Successfully stopped your S3 bridge.\n      You can restart it"
        " by providing your fingerprint to the `bridge` command.",
        fg=typer.colors.GREEN,
    )


@s3.command("delete-bridge", no_args_is_help=True)
def remove_bridge(
    fingerprint: str = typer.Argument(
        ...,
        help="The fingerprint associated with an existing SFTP-bucket bridge.",
    )
) -> None:
    """Shuts down and removes an existing S3 bridge."""
    _, fp_path = utils.fingerprint_path("blackstrap", "s3", fingerprint=fingerprint)
    yaml = fp_path / "docker-compose.yaml"

    print("Removing your S3 bridge...")

    if yaml.exists():
        utils.run_command(["docker-compose", "-f", str(yaml), "down", "--volumes"])
        print()

    shutil.rmtree(fp_path)

    typer.secho("[ ✔ ] Successfully removed your S3 bridge.", fg=typer.colors.GREEN)
