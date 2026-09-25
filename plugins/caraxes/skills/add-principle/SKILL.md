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

The user supplies a proposal, not a finished document. Treat it as incomplete
input that must be clarified and structured before it is written. A valid
principle is universal, stable, normative, observable, and explicit about its
scope. Reject or ask for clarification when it is stack-specific,
project-specific, temporary, a task, a recipe, ambiguous, duplicated, or in
conflict with an existing principle. Do not silently resolve contradictions or
invent missing scope.

When subagent delegation is available, delegate the complete workflow below to
one subagent. Give it the absolute project directory and the user's proposed
principle, and ask it to inspect, validate, and write the external workspace.
The subagent must use the helpers described here and return only a compact
structured result containing the status, principle ID, paths, and conflicts or
clarifications. Do not copy the full index or principle documents back into the
main conversation. Do not run parallel writers against the same workspace.

If delegation is unavailable, perform the same workflow directly. The user’s
explicit invocation authorizes the requested principle write after validation;
it does not authorize resolving a conflict or inventing missing information.

1. Extract the candidate intent from the user's proposal. Identify every
   contradiction, undefined term, and scope gap before drafting anything. At a
   minimum, resolve:
   - the exact normative behavior;
   - the artifact types and situations covered;
   - explicit scope and exclusions, including user-facing content when relevant;
   - exceptions and their justification;
   - how compliance can be observed or verified;
   - whether related artifacts such as commits, issues, pull requests, or
     documentation are included.
   If the user says incompatible things, quote the ambiguity and ask a focused
   clarification question. Do not infer the intended language, scope, or
   exception from context.
2. Inspect the principles directory and read every existing principle returned
   by the helper. Stop on a missing directory, malformed or incomplete
   document, invalid index, or unsafe path.
3. Compare the clarified proposal with all existing principles for exact and
   semantic duplicates, incompatible rules, and accidental stack or project
   scope. Report conflicts instead of choosing a winner.
4. Draft one complete principle with these required sections:
   - `Summary`: one concise sentence that is useful without the full document;
   - `Principle`: one imperative normative rule;
   - `Rationale`: why the rule exists;
   - `Scope`: concrete artifact types, situations, and explicit exclusions;
   - `Implications`: practical consequences, trade-offs, and work affected;
   - `Verification`: observable checks;
   - `Exceptions`: documented exceptions or `None defined`.
   The summary must be semantically faithful to the full rule. Do not add
   artifact categories that the user did not authorize. Keep the document
   readable and focused on one rule.
5. If the proposal passes review and all gaps are resolved, call the helper's
   `add` operation with every required section. Let it allocate the next stable
   `P-###` identifier unless the user supplied one. Use a lowercase hyphenated
   slug. The helper creates the Markdown document and regenerates
   `principles/index.md` atomically without overwriting files.
6. Report the created ID, document path, index path, and the validation result.

The index is an active compact context source. Its summaries must be treated as
rules during the conversation; read the full document when a decision needs
detail or an exception. Do not claim that a principle was added if the helper
did not return a successful JSON result.
