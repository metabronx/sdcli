# `sdcli`

A command-line utility for executing essential and / or laborious tasks.

**Usage**:

```console
$ sdcli [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--install-completion`: Install completion for the current shell.
* `--show-completion`: Show completion for the current shell, to copy it or customize the installation.
* `--help`: Show this message and exit.

**Commands**:

* `gh`: Does things with GitHub's v3 REST API.
* `s3`: Does things with Amazon AWS S3.

## `sdcli gh`

Does things with GitHub's v3 REST API.

**Usage**:

```console
$ sdcli gh [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `assign-teams`: Assigns each user to their metabronx...
* `invite`: Invites the given email or list of emails...
* `login`: yourself.
* `remove`: Removes the given username or list of...

### `sdcli gh assign-teams`

Assigns each user to their metabronx GitHub organization team using the
provided CSV.

**Usage**:

```console
$ sdcli gh assign-teams [OPTIONS] DATA
```

**Arguments**:

* `DATA`: A csv text file of usernames and team memberships, without a header.  [required]

**Options**:

* `--help`: Show this message and exit.

### `sdcli gh invite`

Invites the given email or list of emails to the metabronx GitHub organization. A
list of emails must be a UTF-8 text file, where each email is on a separate line.
Invited users are automatically added to the "members" team, unless other options
are given.

**Usage**:

```console
$ sdcli gh invite [OPTIONS] [EMAIL]
```

**Arguments**:

* `[EMAIL]`: The email address of the person to invite. This option is mutually exclusive with `--from-file`.

**Options**:

* `--team TEXT`: The organization teams to which to invite the person(s). Pass this option multiple times to include more than one team. Defaults to 'members'.
* `--from-file FILENAME`: A line-delimited text file of email address to invite. This option is mutually exclusive with supplying a single email address.
* `--help`: Show this message and exit.

### `sdcli gh login`

yourself. To avoid saving your credentials on your host machine, you may export
the GH_USERNAME and GH_TOKEN environment variable or pass them to every command.

Credentials are stored in plain-text at `~/.sdcli/credentials`.

**Usage**:

```console
$ sdcli gh login [OPTIONS]
```

**Options**:

* `--help`: Show this message and exit.

### `sdcli gh remove`

Removes the given username or list of usernames from the metabronx GitHub
organization. A list of usernames must be a text file, where each username is on a
separate line.

**Usage**:

```console
$ sdcli gh remove [OPTIONS] [USERNAME]
```

**Arguments**:

* `[USERNAME]`: The username of the person to remove. This option is mutually exclusive with `--from-file`.

**Options**:

* `--from-file FILENAME`: A line-delimited text file of usernames to remove. This option is mutually exclusive with supplying a single username.
* `--help`: Show this message and exit.

## `sdcli s3`

Does things with Amazon AWS S3.

**Usage**:

```console
$ sdcli s3 [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `bridge`: Bridges an S3 object store (bucket) to an...
* `delete-bridge`: Shuts down and removes an existing S3 bridge.
* `stop-bridge`: Shuts down an existing S3 bridge.

### `sdcli s3 bridge`

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
* `--help`: Show this message and exit.

### `sdcli s3 delete-bridge`

Shuts down and removes an existing S3 bridge.

**Usage**:

```console
$ sdcli s3 delete-bridge [OPTIONS] FINGERPRINT
```

**Arguments**:

* `FINGERPRINT`: The fingerprint associated with an existing SFTP-bucket bridge.  [required]

**Options**:

* `--help`: Show this message and exit.

### `sdcli s3 stop-bridge`

Shuts down an existing S3 bridge.

**Usage**:

```console
$ sdcli s3 stop-bridge [OPTIONS] FINGERPRINT
```

**Arguments**:

* `FINGERPRINT`: The fingerprint associated with an existing SFTP-bucket bridge.  [required]

**Options**:

* `--help`: Show this message and exit.
