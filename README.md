# OpenRiak Admin Tools

Scripting for administering stuff in the repos.

## Getting Started

Invoke `bin/gh-admin -h` to see what it offers.

This lists the commands and options.

### Configuration

A great deal of what the script does is driven by file-based configuration.

In _most_ cases, the default configuration will work fine, but if you want to
alter it copy [./etc/config.json](etc/config.json) to the directory from which
you'll be running the script and make your changes in the **copy**.

The [configuration schema](schema/gh-admin.config.schema.json) is fairly well
documented for consumption by an editor that understands JSON schemas - such
an editor _should_ provide you with hints about what you can, and can't, put
in your config file, provided that you kept the `"$schema"` key from the
original file.

### Credentials

All commands that interact with GitHub require you to have a GitHub account,
as GitHub's REST API is severely rate-limited.
Many operations would just fail due to the rate-limiting, so unauthenticated
access is not supported.

By default, the script looks for a files named `.github.credentials` in your
$HOME directory containing the line

```
github.token=ghp_...
```

where the value associated with the `github.token` key is a GitHub access
token (starting with `ghp_`) obtained while logged into your GitHub account.

You can learn about creating access tokens in the
[GitHub Help](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-fine-grained-personal-access-token),
and a template for a `read-only` token can be accessed via the
[GitHub Web UI](https://github.com/settings/personal-access-tokens/new?name=Repo-reading+token&description=Just+contents:read&contents=read).

***BE SURE*** to copy the token you create before closing the page - access
tokens ***CANNOT*** be retrieved at a later time!

It is ***strongly*** recommended that you set restrictive permissions on the
credential file with the command:

```
chmod 0400 ~/.github.credentials
```

### Caveats

Very much WiP, YMMV, etc... Use at your own risk.

## Bugs?

Yeah, probably.
