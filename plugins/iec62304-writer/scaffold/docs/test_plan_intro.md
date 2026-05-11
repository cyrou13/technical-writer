<!--
  Narrative sections of the Software Test Description (STD).
  The build (`tools/build_docs.py`) inlines the sections below into
  `docs/generated/30_STD.md`.

  Recognized sections:
    ## test-strategy   → STD Section 3
    ## test-pass-fail  → Section 4 (overrides the default)
    ## test-exclusions → Section 7

  Any other H2 is ignored. Edit by hand — no agent touches this file.
-->

## test-strategy

[TODO Describe the test strategy:

- targeted levels (unit / integration / system / E2E),
- methodology (TDD/BDD/test-after, coverage requirement),
- tooling (Vitest/Jest, pytest, Playwright/Cypress…),
- frequency and triggers (pre-commit, CI on PR, nightly),
- automation scope vs manual tests,
- management of fixtures and test data.]

## test-exclusions

[TODO List what is NOT tested automatically and why:

- third-party components handled as black boxes (with justification),
- environments not covered (mobile, legacy browsers…),
- load / performance scenarios out of scope for v1,
- accessibility tests deferred.]
