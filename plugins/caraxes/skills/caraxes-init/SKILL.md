---
name: caraxes-init
description: Initialize or locate the user's external Caraxes workspace for Spec-Driven Development (SDD), including its principles, stacks, projects, and work directories. Use when the user asks to set up Caraxes or find its workspace.
---

Use the bundled [workspace helper](scripts/workspace.py) to resolve the workspace
from persistent configuration on every invocation. Do not infer it from chat memory
or store workspace data in the plugin installation or the target project.

1. Identify the target project's absolute directory from the current context. If
   there is no project context, ask which project directory to keep separate.
2. Find Python 3.9 or newer (`python3`, `python`, or `py -3` on Windows). If none is
   available, report the prerequisite rather than installing software implicitly.
3. For a lookup, run `workspace.py resolve --project <absolute-project-directory>`.
   This operation is read-only. For setup, run `workspace.py init --project
   <absolute-project-directory>`. Resolve the script path relative to this SKILL.md
   and quote filesystem paths appropriately for the actual shell.
4. Add `--workspace <absolute-directory>` to init only when the user selected a
   custom location. Otherwise reuse the registered workspace, or initialize the
   default `<user-home>/.caraxes/workspace` on first use. An explicit path
   selects the workspace itself; do not append another directory name.
5. Respect filesystem permissions. If Codex blocks a write outside the project,
   use its approval mechanism for the intended path; do not move data into the
   project or disable the sandbox to get around the restriction.
6. Read the JSON result. On success, report the absolute workspace path and which
   directories were created or missing. Leave all four directories for the user
   to populate. On failure, explain the error and stop; do not reset configuration,
   switch workspaces, remove locks, or recreate a missing registered workspace.

The helper stores the pointer in `<user-home>/.caraxes/config.json`. Repeating init
preserves existing content and repairs missing child directories. It does not
migrate workspaces, initialize Git, generate specifications, or implement the rest
of the SDD workflow. For a resolve result with `status: incomplete`, report the
missing directories and offer initialization instead of writing during lookup.
