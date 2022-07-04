# sdcli

![GitHub Workflow Status](https://img.shields.io/github/workflow/status/metabronx/sdcli/CI?label=tests&style=flat-square)

A metabronx command line tool for automating important grunt work.

Current features include:

- Inviting members to the `metabronx` GitHub organization and teams, individually or in bulk:

  ```bash
  sdcli gh invite --help
  ````

- Assign members in bulk to teams in the `metabronx` GitHub organization:

  ```bash
  sdcli gh assign-teams --help
  ````

## Use

Run `python3 -m pip install git@github.com:metabronx/sdcli.git` to install.

You can view command help with `sdcli --help`.
