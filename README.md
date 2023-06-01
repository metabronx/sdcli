# sdcli

![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/metabronx/sdcli/ci.yaml?label=tests&style=flat-square)

A command-line utility for executing essential but laborious tasks.

**Usage**:

```console
$ sdcli [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `gh`: Does things with GitHub's v3 REST API.

## `sdcli gh`

Does things with GitHub's v3 REST API.

**Usage**:

```console
$ sdcli gh [OPTIONS] COMMAND [ARGS]...
```

**Options**:

* `--help`: Show this message and exit.

**Commands**:

* `assign-teams`: Assigns each user to their metabronx GitHub...
* `auth`: Authenticates your machine with GitHub so any...
* `invite`: Invites the given email or list of emails to...
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

### `sdcli gh auth`

Authenticates your machine with GitHub so any future requests are executed as
yourself. To avoid saving your credentials on your host machine, you may export
the GH_USERNAME and GH_TOKEN environment variable or pass them to every command.

Credentials are stored in plain-text at `~/.sdcli/credentials`.

**Usage**:

```console
$ sdcli gh auth [OPTIONS]
```

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
