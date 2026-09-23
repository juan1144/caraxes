# Test structure

Caraxes tests are organized by scope and domain:

- `unit/`: isolated helper and validation tests, grouped by domain.
- `integration/`: filesystem, plugin installation, and component interaction tests.
- `behavioral/`: representative Codex requests and expected skill behavior.

Create a directory only when that test scope exists. Keep test names in English
and describe observable behavior. Shared fixtures belong under the nearest scope
when they are genuinely reused; avoid a global fixtures directory until that need
appears.
