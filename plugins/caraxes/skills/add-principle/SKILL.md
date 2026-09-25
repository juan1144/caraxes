---
name: add-principle
description: Add a universal Caraxes principle to the external workspace after validating its scope, clarity, duplication, and conflicts. Use when the user asks to create or register a cross-project, cross-stack principle.
---

Add principles only to the external Caraxes workspace. Never store them in the
target project or plugin installation.

Use the bundled `scripts/principles.py` helper for workspace inspection and
file writes. Resolve the workspace by running the existing
`../init/scripts/workspace.py resolve --project <absolute-project-directory>`
helper before calling this script. If no workspace is registered, stop and tell
the user to run `$caraxes:init`.

The user supplies the idea in the conversation; this workflow controls how it
is classified and written. A valid principle is universal, stable, normative,
and observable. Reject or ask for clarification when it is stack-specific,
project-specific, temporary, a task, a recipe, ambiguous, duplicated, or in
conflict with an existing principle. Do not silently resolve conflicts.

1. Inspect the principles directory and read every existing principle returned
   by the helper. Stop on a missing directory, malformed document, invalid
   index, or unsafe path.
2. Decide whether the proposal is a single cross-project rule. Use imperative
   language and keep the summary to one concise sentence that is useful on its
   own. Keep the detailed document small; include only the title, summary, and
   rule in this first version.
3. Compare the proposal with all existing principles for exact and semantic
   duplicates, incompatible rules, and accidental stack or project scope.
4. If the proposal passes review, use the helper's `add` operation. Let it
   allocate the next stable `P-###` identifier unless the user supplied one.
   Use a lowercase hyphenated slug. The helper creates the Markdown document
   and regenerates `principles/index.md` atomically without overwriting files.
5. Report the created ID, document path, index path, and the validation result.

The index is an active compact context source. Its summaries must be treated as
rules during the conversation; read the full document when a decision needs
detail or an exception. Do not claim that a principle was added if the helper
did not return a successful JSON result.
