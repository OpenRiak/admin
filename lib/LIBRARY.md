# Library Components

The library is organized with one file per module for simplicity, rather than
the directory-per-module Python pattern.
*Most* modules contain only one substantive class.

## Substantive Classes

* All of these classes require `scr.CONFIG` to be initialized as a `Config`
  mapping object when they are instantiated.
* These classes _DO NOT_ accept constructor parameters as Python has no clean
  way to ensure all classes in a multi-inheritance graph receive their
  parameters without passing it/them to the base `object` class which doesn't
  accept them.
* By convention, instance member function names begin with a lowercase letter
  _ONLY_ if they are to be exposed as commands.

### `cmd.CommandDispatcher`

* Mixin class providing dynamic command invocation.
* All classes providing commands register statically at module load.

### `gh.GitHubRest`

* Base class underlying all `GitHub*` operation classes.
* Each instance is specific to a single GitHub organization.
* Handles authorization context, API versioning, and content types.
* Provides access to the core GitHub CRUD operations.
  * `PUT`, `GET`, `POST`, `DELETE`, etc.
* Provides low-level protected operations for record iteration, filtering, and mapping.

### `ghactor.GitHubActors`

* Extends `gh.GitHubRest`
* Provides protected operations for working with organization members.

### `ghactorcmd.GitHubActorCmds`

* Extends `cmd.CommandDispatcher` and `ghactor.GitHubActors`
* Provides public commands for interacting with organization members.

### `ghrepo.GitHubRepos`

* Extends `ghactor.GitHubActors`
* Provides protected operations for working with repositories.

### `ghrepocmd.GitHubRepoCmds`

* Extends `cmd.CommandDispatcher` and `ghrule.GitHubRepos`
* Provides public commands for interacting with repositories.

### `ghrule.GitHubRules`

* Extends `ghrepo.GitHubRepos`
* Provides protected operations for working with repository rulesets.

### `ghrulecmd.GitHubRuleCmds`

* Extends `cmd.CommandDispatcher` and `ghrule.GitHubRules`
* Provides public commands for interacting with repository rulesets.

## Helper Classes

### `cmd.CommandError`

* Exception reporting command invocation/execution errors.

### `gh.GitHubError`

* Exception reporting GitHub initialization/invocation errors.

### `cmd.Indent`

* Provides a stateful indenting context for output text.

### `jsoncmd.JsonCommand`

* Helper for commands that read or write JSON.

## Common Script Support

### The `scr` Module

Common constants and utility functions.

### The `libpath` Module

This module lives in the `scr.BIN_DIR` directory and, upon import, adds
`scr.LIB_DIR` to the Python module search path.

It exposes no API and is intended solely to be the first import in scripts in
the `scr.BIN_DIR` directory.
