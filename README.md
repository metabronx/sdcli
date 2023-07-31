# sdcli

![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/metabronx/sdcli/ci.yaml?label=tests&style=flat-square)

A command-line utility for executing essential but laborious tasks.

Tested support on Python 3.7, 3.8, 3.9, 3.10, and 3.11 on macOS, Windows, and Linux.  
Operating system versions are supplied by [GitHub Actions](https://docs.github.com/en/actions/using-jobs/choosing-the-runner-for-a-job#choosing-github-hosted-runners).

## Installation

You can install this package via pip:

```sh
$ pip install git+https://github.com/metabronx/sdcli.git
$ sdcli --help
```

## Usage

sdcli's commands are organized by the application with which the tool interfaces.

### `sdcli gh`

This does things with GitHub's v3 REST API via the following subcommands:

- `auth`: Authenticates your machine with GitHub.
- `invite`: Invites the given email(s) to the metabronx organization.
- `assign-teams`: Assigns users to their metabronx organization team.
- `remove`: Removes the given username(s) from the metabronx organization.

#### `sdcli gh auth`

Authenticates your machine with GitHub so any future requests are executed as yourself. To avoid saving your credentials on your host machine, you may export the `GH_USERNAME` and `GH_TOKEN` environment variable or pass them to every command.

Credentials are stored in plain-text at `~/.sdcli/credentials`.

**Usage**:

```console
$ sdcli gh auth
```

#### `sdcli gh assign-teams`

Assigns each user to their metabronx GitHub organization team using the provided CSV.

If the authenticated user is an organization Owner, and the users to assign are not already a part of the organization, they will also receive invites. Upon acceptance, they will be assigned to the team in the CSV.

**Usage**:

```console
$ sdcli gh assign-teams DATA
```

**Arguments**:

- `DATA`: The path to a CSV text file of usernames and team memberships in the format `username,team`. For example:

  ```csv
  NakoTo7,members
  Shreyaaashetty,members
  sultanax,members
  tanvircode,members
  ```

### `sdcli gh invite`

Invites the given email or list of emails to the metabronx GitHub organization. A list of emails must be a UTF-8 text file, where each email is on a separate line. Invited users are automatically added to the "members" team, unless other options are given.

**Usage**:

```console
$ sdcli gh invite [OPTIONS] [EMAIL]
```

**Arguments**:

- `[EMAIL]`: The email address of the person to invite. This option is mutually exclusive with `--from-file`.

**Options**:

- `--from-file FILENAME`: A line-delimited text file of email address to invite. This option is mutually exclusive with supplying a single email address.
- `--team TEXT`: The organization teams to which to invite the person(s). Pass this option multiple times to include more than one team. Defaults to 'members'.

### `sdcli gh remove`

Removes the given username or list of usernames from the metabronx GitHub organization. A list of usernames must be a text file, where each username is on a separate line.

**Usage**:

```console
$ sdcli gh remove [OPTIONS] [USERNAME]
```

**Arguments**:

- `[USERNAME]`: The username of the person to remove. This option is mutually exclusive with `--from-file`.

**Options**:

- `--from-file FILENAME`: A line-delimited text file of usernames to remove. This option is mutually exclusive with supplying a single username.

### `sdcli s3` [🏴‍☠️]

This does things with Amazon AWS S3 via the following subcommands:

- `bridge`: Exposes S3 via a local SFTP connection (a "bridge").
- `stop-bridge`: Shuts down a bridge.
- `remove-bridge`: Shuts down and removes all data for a bridge.

#### `sdcli s3 bridge`

Bridges an S3 object store (bucket) to an SFTP-accessible file system.

**Usage**:

```console
$ sdcli s3 bridge [OPTIONS]
```

**Options**:

* `--fingerprint TEXT`: The fingerprint associated with an existing SFTP-bucket bridge. This option is mutually exclusive with all other options.
* `--bucket TEXT`: The bucket to expose via SFTP. When you supply this for the first time, you must also supply access credentials.
* `--access-key-id TEXT`: Your AWS Access Key ID. This must be supplied when first connecting to a bucket.
* `--secret-access-key TEXT`: Your AWS Secret Access Key. This must be supplied when first connecting to a bucket.
* `--force-restart`: By default, existing S3 bridges will not be restarted if they're already running. Specify this flag to override this behavior. This is equivalent to the `--force-recreate` flag provided Docker Compose.

#### `sdcli s3 stop-bridge`

Shuts down an existing S3 bridge.

**Usage**:

```console
$ sdcli s3 stop-bridge FINGERPRINT
```

**Arguments**:

* `FINGERPRINT`: The fingerprint associated with an existing SFTP-bucket bridge.  [required]

#### `sdcli s3 delete-bridge`

Shuts down and removes an existing S3 bridge.

**Usage**:

```console
$ sdcli s3 delete-bridge FINGERPRINT
```

**Arguments**:

* `FINGERPRINT`: The fingerprint associated with an existing SFTP-bucket bridge.  [required]

## License

Elias
