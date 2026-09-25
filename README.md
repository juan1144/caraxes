# Caraxes

A Codex plugin for Spec-Driven Development (SDD), keeping specifications and
working context outside the repositories where features are implemented.

## Current capability

`init` initializes or locates one personal workspace. It replaces the
practice greeting skill. The rest of the SDD workflow is not implemented yet.

```text
<user-home>/
└── .caraxes/
    ├── config.json
    └── workspace/
        ├── principles/
        ├── stacks/
        ├── projects/
        └── work/
```

The four workspace directories start empty and are populated by the user.
`config.json` stores `schema_version: 1` and an absolute `workspace_path`. It lives
outside the workspace, so custom workspaces retain the same four-directory layout.

Caraxes resolves the current user's home directory at runtime. Typical locations
are `/home/alex` on Linux, `/Users/alex` on macOS, and `C:\Users\Alex` on Windows;
these paths are examples, not hardcoded assumptions. In WSL, containers, or remote
sessions, this is the home directory of that execution environment.

The `.caraxes` location is a Caraxes convention, not an OpenAI requirement. A dot
in a directory name does not make it private. New leaf directories request owner-only
permissions on POSIX; existing permissions are preserved and Windows uses its ACLs.

## Install and use

Requires Codex with plugin support and Python 3.9 or newer. The helper uses only
the Python standard library. Python must be installed separately if unavailable;
the plugin does not install it.

From this repository root, register and install the local plugin:

```bash
codex plugin marketplace add "$PWD"
codex plugin add caraxes@personal --json
codex plugin list --marketplace personal --json
```

In PowerShell, use `(Get-Location).Path` instead of `"$PWD"` for the first command.
The catalog uses the scaffold's default name `personal`. Resolve any conflict with
an existing marketplace of that name before registering it.

Start a **new Codex conversation** in the target project after installation:

```text
Use $caraxes:init to initialize my external SDD workspace.
```

For a custom location on first initialization:

```text
Use $caraxes:init with /absolute/path/to/my-specs as the workspace.
```

The specified path is the workspace itself. Later requests reuse its saved location:

```text
Use $caraxes:init to locate my workspace without changing anything.
```

Codex may request approval to write outside the project. Grant access to the
intended Caraxes location through the host's permissions flow. Installing the plugin
does not automatically grant filesystem access.

## Helper behavior

The skill invokes `plugins/caraxes/skills/init/scripts/workspace.py` from
its installed location. For development, run it directly from this repository:

```bash
python3 plugins/caraxes/skills/init/scripts/workspace.py init --project /absolute/project
python3 plugins/caraxes/skills/init/scripts/workspace.py resolve --project /absolute/project
```

Use `py -3` or a verified Python 3 interpreter on Windows. Quote paths with spaces.
Both operations return JSON; operational failures return exit code 1 and JSON on
stderr. CLI syntax errors use argparse's standard error output.

- `init` creates missing directories and registers the absolute location after
  successful creation. Repeat runs preserve existing content and configuration.
- `resolve` only reads. Missing child directories produce `status: incomplete` and
  a list; a later explicit init can repair them.
- Missing registered workspaces and malformed configurations cause an error. Caraxes
  does not silently recreate, relocate, reset, or migrate them.
- Different custom paths are rejected after registration. Workspace switching is
  outside this first version's scope.
- Target-project paths and paths inside detected Git repositories are rejected
  after symlink resolution. The supplied project boundary also protects non-Git
  projects. Required child directories cannot be symlinks or files.
- Configuration is written via a temporary file and atomic replacement under an
  exclusive registration lock. Failed initialization may leave created empty
  directories, but does not delete existing data. A leftover `.init.lock` requires
  investigation; the helper does not automatically remove another run's lock.

The helper protects against ordinary mistakes, not hostile concurrent filesystem
changes. It cannot discover every non-Git project on a machine; pass the actual
project directory to establish that boundary.

## Repository structure

```text
.agents/plugins/marketplace.json     Repository plugin catalog
AGENTS.md                           Contribution and language conventions
plugins/caraxes/.codex-plugin/plugin.json
plugins/caraxes/skills/init/
    SKILL.md                        Agent instructions and discovery metadata
    scripts/workspace.py            Initialization and read-only resolution
tests/unit/workspace/test_workspace.py
                                    Isolated filesystem tests
```

The marketplace's `./plugins/caraxes` source is relative to the repository root.
The supported Codex compatibility manifest is generated by plugin-creator; this
project does not mix it with the newer portable root-manifest format.

## Validation

Run the tests from the repository root:

```bash
python3 -m unittest discover -s tests -v
```

Tests use temporary directories, not the user's real workspace. They cover default
and custom paths, persistence, idempotence, read-only resolution, corrupt/missing
state, project boundaries, symlinks, conflicting files, and filesystem failures.
They have been run on Linux; native Windows and macOS runs remain pending.

The bundled plugin-creator and skill-creator validators check manifest and skill
structure. Installation is checked separately using `codex plugin list`.

For the fresh-session smoke test, invoke init and verify that Codex loads
its installed SKILL.md and executes the bundled helper. Check the returned absolute
path and the four empty directories. Repeat init after adding a note and verify it
is preserved; use resolve and verify that it makes no changes. Do not count
successful installation alone as a behavioral test of the skill.

## Official references

- [Plugin architecture](https://developers.openai.com/plugins/concepts/plugins)
- [Plugin packaging](https://developers.openai.com/plugins/build/plugins)
- [Building skills](https://developers.openai.com/plugins/build/skills)
- [Codex permissions](https://learn.chatgpt.com/docs/permissions)
