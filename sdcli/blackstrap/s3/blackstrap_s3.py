from pathlib import Path
from string import Template
from typing import Optional

import typer

from sdcli.utils import fingerprint_path, is_docker_supported, run_command

# s3 = typer.Typer(
#     help="Bridges an S3 object store (bucket) to an SFTP-enabled file system.",
# )


# @s3.command()
def bridge(
    fingerprint: Optional[str] = typer.Option(
        None,
        help="The fingerprint associated with an existing SFTP-bucket bridge. This"
        " option is mutually exclusive with `--mount`.",
    ),
    bucket: Optional[str] = typer.Option(
        None,
        help="The bucket to expose via SFTP. This option is mutually exclusive with"
        " `--fingerprint`. When you supply this for the first time, you must also"
        " supply an ",
    ),
    access_key_id: Optional[str] = typer.Option(
        None,
        help="Your AWS Access Key ID. This must be supplied when first connecting"
        "to a bucket.",
    ),
    secret_access_key: Optional[str] = typer.Option(
        None,
        help="Your AWS Secret Access Key. This must be supplied when first"
        " connecting to a bucket.",
    ),
    ssh_pubkey: Path = typer.Option(
        "~/.ssh/id_ed25519.pub",
        help="Your public SSH key. This must be supplied when first connecting to a"
        "bucket, and will only ever be used for local SFTP access.",
    ),
):
    """Bridges an S3 object store (bucket) to an SFTP-enabled file system."""
    is_docker_supported()

    yaml = (
        fingerprint_path("blackstrap", "s3", fingerprint=fingerprint, hashable=bucket)
        / "docker-compose.yaml"
    )
    if not yaml.exists():
        print("New bucket information provided. Configuring a new bridge...")

        # check if access credentials exist
        if not access_key_id or not secret_access_key:
            typer.secho(
                "[ X ] You must supply both an AWS Access Key ID and AWS Secret Access"
                " Key to configure a new S3 bridge.",
                fg=typer.colors.BRIGHT_RED,
            )
            raise typer.Exit(code=1)

        # check if the there is a local public SSH key
        ssh_pubkey = ssh_pubkey.expanduser().resolve()
        if not ssh_pubkey.is_file():
            typer.secho(
                "[ X ] You must supply an SSH public key to use for local SFTP.",
                fg=typer.colors.BRIGHT_RED,
            )
            raise typer.Exit(code=1)

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
                        "SSH_PUBKEY": str(ssh_pubkey),
                    }
                )
            )
    else:
        print("Existing S3 bridge configuration found.")

    print("Your S3 bridge is starting. This may take a few seconds.")
    run_command(f"docker compose -f {yaml} up --wait")

    typer.secho(
        "\n[ ✔ ] Successfully started your S3 bridge!\n      The service has the"
        f" fingerprint: {yaml.parent.name}. You can use it to start this bridge again"
        " without having to provide all the same bucket and access credentials.\n"
        "      Connect to your bucket via SFTP at `blackstrap-user@localhost:1111`.",
        fg=typer.colors.GREEN,
    )
