import hashlib
import platform
import shutil
import subprocess
from pathlib import Path
from string import Template
from typing import Optional, Union

import typer

from ..utils import run_command

blackstrap = typer.Typer()


def _check_docker():
    """Checks if Docker and Docker Compose 2 exist on the system."""
    try:
        subprocess.run(["docker", "version"], capture_output=True, check=True)
        docker_check = subprocess.run(
            ["docker", "compose", "version"], capture_output=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        docker_check = None

    if not docker_check or docker_check.returncode != 0:
        typer.secho(
            "[ X ] Docker Compose is not available but is required. Ensure Docker and"
            " Docker Compose 2 are installed and running before continuing.",
            fg=typer.colors.BRIGHT_RED,
        )
        raise typer.Exit(code=1)


def _check_wsl():
    """Checks if on Windows and WSL is using the correct Linux kernel."""
    wslconfig = Path.home() / ".wslconfig"
    kernel = Path.home() / ".sdcli" / "wsl-kernel"

    # check if on Windows and
    # 1. .wslconfig exists
    # 2. the custom kernel exists
    # 3. if the .wslconfig says to use the custom kernel
    if platform.system() == "Windows" and (
        not wslconfig.exists()
        or not kernel.exists()
        or not f"kernel={kernel}" not in wslconfig.read_text()
    ):
        typer.secho(
            "[ X ] You are running Windows, but the default Linux kernel used by WSL"
            " isn't configured correctly for use with Wireguard. Run `sdcli vpn"
            " setup-wsl` to download and install a pre-built custom kernel.",
            fg=typer.colors.BRIGHT_RED,
        )
        raise typer.Exit(code=1)


def _fingerprint_path(
    fingerprint: Optional[str] = None, hashable: Union[Optional[Path], str] = None
) -> Path:
    """Returns the cache path for a given fingerprint or hashable."""
    if (not fingerprint and not hashable) or (fingerprint and hashable):
        typer.secho(
            "[ X ] You must supply either the fingerprint of an already configured"
            " service or the path of a directory to mount.",
            fg=typer.colors.BRIGHT_RED,
        )
        raise typer.Exit(code=1)

    path = (
        Path.home()
        / ".sdcli"
        / "blackstrap"
        / (
            fingerprint
            or hashlib.md5(str(hashable).encode(), usedforsecurity=False).hexdigest()
        )
    )

    if fingerprint and not path.exists():
        typer.secho(
            """[ X ] The fingerprint provided does not exist.""",
            fg=typer.colors.BRIGHT_RED,
        )
        raise typer.Exit(code=1)

    return path


@blackstrap.callback()
def _check_prerequisites(ctx: typer.Context):
    """Checks that all system prerequisites have been met."""
    _check_docker()

    if ctx.invoked_subcommand != "setup-wsl":
        _check_wsl()


@blackstrap.command("setup-wsl")
def wsl():
    """
    Downloads and configures Windows Subsystem for Linux to use blackstrap's pre-built
    Linux kernel. This is required to support peer connections on Windows machines.

    ! [WARNING] !
    This will replace the contents of your local .wslconfig. Download and add the
    kernel manually (~/.sdcli/wsl-kernel) if wish to keep it.
    """
    print("Downloading the kernel...")
    run_command(
        [
            "docker",
            "create",
            "--rm",
            "--name",
            "setup-wsl",
            "ghcr.io/metabronx/blackstrap-wsl-kernel",
        ]
    )
    kernel = Path.home() / ".sdcli" / "wsl-kernel"
    kernel.parent.mkdir(exist_ok=True)
    run_command(["docker", "cp", "setup-wsl:/kernel", str(kernel)])

    print("Patching WSL...")
    wslconfig = Path.home() / ".wslconfig"
    wslconfig.write_text(f"[boot]\nsystemd=true\n\n[wsl2]\nkernel={kernel}")

    run_command("wsl --shutdown")

    typer.secho(
        "\n[ ✔ ] Successfully configured WSL. Ensure to restart Docker Desktop.",
        fg=typer.colors.GREEN,
    )


@blackstrap.command("start")
def start(
    fingerprint: Optional[str] = typer.Option(
        None,
        help="The fingerprint associated with an existing and live VPN service. This"
        " option is mutually exclusive with `--mount`.",
    ),
    mount: Optional[Path] = typer.Option(
        None,
        help="The directory to expose to client VPN connections. This option is"
        " mutually exclusive with `--fingerprint`.",
    ),
):
    """Starts a Wireguard VPN filesystem bridge"""

    # check if the provided mount is a directory and not ./remote
    if mount:
        if not mount.is_dir():
            typer.secho(
                "[ X ] The mount to expose must be a directory, but can be empty.",
                fg=typer.colors.BRIGHT_RED,
            )
            raise typer.Exit(code=1)
        elif mount.name == "remote":
            typer.secho(
                "[ X ] The mount directory cannot end in 'remote'.",
                fg=typer.colors.BRIGHT_RED,
            )
            raise typer.Exit(code=1)

    # construct the expected path of the a cached server compose yaml
    yaml = _fingerprint_path(fingerprint=fingerprint, hashable=mount) / "server.yaml"

    # if it doesn't exist, copy the template from here, apply the changes, and save it
    if not yaml.exists():
        assert mount

        yaml.parent.mkdir(parents=True, exist_ok=True)
        templ_yaml = Path(__file__).with_name("server.yaml")

        with templ_yaml.open("r") as f:
            template = Template(f.read())
            yaml.write_text(
                template.substitute(
                    {
                        "MOUNT": str(mount.absolute()),
                        "FPDIR": str(yaml.parent),
                    }
                )
            )

        yaml.with_name("vpn-configs").mkdir()
        shutil.copy(templ_yaml.with_name("npeers"), yaml.with_name("npeers"))

    print("The VPN server is starting. This may take a few seconds.")
    run_command(f"docker compose -f {yaml} up --wait")

    typer.secho(
        "\n[ ✔ ] Successfully started a VPN server!\nThe service has the fingerprint:"
        f" {yaml.parent.name}. Keep track of this if you intend to add clients to the"
        " tunnel.",
        fg=typer.colors.GREEN,
    )


@blackstrap.command("add-client")
def add_client(
    fingerprint: str = typer.Option(
        ..., help="The fingerprint associated with an existing and live VPN service."
    )
):
    """Adds a client to the VPN service associated with the provided fingerprint."""
    npeers = _fingerprint_path(fingerprint=fingerprint) / "npeers"

    # read the npeers file in and increment the number by 1
    num = int(npeers.read_text().split("=")[1]) + 1
    npeers.write_text(f"PEERS={num}")

    # restart the VPN services to allow Wireguard to generate the new peer configs
    print("The VPN server is restarting. This might take a few seconds.")
    yaml = npeers.with_name("server.yaml")
    run_command(f"docker compose -f {yaml} down")
    run_command(f"docker compose -f {yaml} up --wait")

    # generate ssh keys and send croc package
    print("Configuring a new client...")
    subprocess.call(
        [
            "docker",
            "compose",
            "-f",
            str(yaml),
            "exec",
            "blackstrap",
            "/scripts/add-client.sh",
            str(num),
        ]
    )

    typer.secho(
        "\n[ ✔ ] Successfully configured a new client! They should be able to connect"
        f" under the peer{num} identity using `sdcli vpn connect`.",
        fg=typer.colors.GREEN,
    )


@blackstrap.command("connect")
def connect(
    name: str = typer.Option(..., help="A name to give the new VPN connection."),
    code: Optional[str] = typer.Option(
        None, help="The code provided by `add-client` with started VPN service."
    ),
    mount: Optional[Path] = typer.Option(
        None,
        help="The directory to which to mount the VPN. It must be empty.",
    ),
):
    """Configures a new VPN connection with remote filesystem."""

    # construct the expected path of the a cached client compose yaml
    yaml = _fingerprint_path(hashable=name) / "client.yaml"

    # if it doesn't exist, copy the template from here, apply the changes, and save it
    if not yaml.exists():
        print("No existing VPN profile found. A new one will be created.")

        # ensure an empty non-reserved directory was given as a mount point
        if (
            not mount
            or not mount.exists()
            or not mount.is_dir()
            or len([p for p in mount.iterdir()]) > 0
        ):
            typer.secho(
                "[ X ] You must supply an empty directory for the VPN service to use.",
                fg=typer.colors.BRIGHT_RED,
            )
            raise typer.Exit(code=1)

        # check if a code was given
        if not code:
            typer.secho(
                "[ X ] You must supply a server-provided code to establish new VPN"
                " connections.",
                fg=typer.colors.BRIGHT_RED,
            )
            raise typer.Exit(code=1)

        yaml.parent.mkdir(parents=True, exist_ok=True)
        templ_yaml = Path(__file__).with_name("client.yaml")

        with templ_yaml.open("r") as f:
            template = Template(f.read())
            yaml.write_text(
                template.substitute(
                    {
                        "MOUNT": str(mount.absolute()),
                        "FPDIR": str(yaml.parent),
                    }
                )
            )

        yaml.with_name("vpn-configs").mkdir()

        # download the croc package and put the files in the right places
        print("Configuring the VPN profile. This might take a few seconds.")
        subprocess.call(
            [
                "docker",
                "compose",
                "-f",
                str(yaml),
                "run",
                "--quiet-pull",
                "--rm",
                "--entrypoint=''",
                "--workdir",
                "/config",
                "blackstrap",
                "/scripts/install-client.sh",
                code,
            ]
        )

    # boot the wireguard client and filesystem bridge
    print("Starting the VPN client. This might take a few more seconds.")
    run_command(f"docker compose -f {yaml} down")
    run_command(f"docker compose -f {yaml} up --force-recreate --wait")

    print("Connecting filesystems...")
    run_command(
        [
            "docker",
            "compose",
            "-f",
            str(yaml),
            "exec",
            "--workdir",
            "/config",
            "blackstrap",
            "/scripts/mountfs.sh",
        ]
    )

    typer.secho(
        "\n[ ✔ ] Successfully connected! You should see the remote filesystem at your"
        " mount point.",
        fg=typer.colors.GREEN,
    )
