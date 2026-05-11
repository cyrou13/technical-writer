#!/usr/bin/env python3
"""Generate ready-to-paste Claude Code prompts to close coverage gaps.

For every SRS item that lacks an implementing SDS or a verifying TC,
emits up to 3 prompt files under `docs/generated/prompts/`:
  - <SRS-ID>-impl.md       — prompt to implement the missing code
  - <SRS-ID>-unit-tests.md — prompt to write the unit tests
  - <SRS-ID>-e2e.md        — prompt for Playwright E2E (only if UI signal)

UI detection heuristics:
  - SRS source paths include `*.tsx`, `*.vue`, `*.svelte`, `*.jsx`,
    `frontend/`, `ui/`, `web/`, `viewer/`
  - SRS has a parent USC (use scenario) → user-facing
  - SRS title/description mentions "user", "screen", "page", "form"

Reads:
    docs/items/SRS/*.md          (target requirements)
    docs/items/SDS/*.md          (existing implementations)
    docs/items/TC/*.md           (existing tests)
    docs/items/USC/*.md          (use scenarios — UI context)
    dt-config.yaml               (product metadata)
    docs/dt-clinical-context.md  (intended use, end users)

Writes:
    docs/generated/prompts/<SRS-ID>-{impl,unit-tests,e2e}.md
    docs/generated/prompts/_index.md   (catalogue + paste-and-go links)

Stdlib only. Python 3.12+.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import (  # noqa: E402
    Item,
    load_clinical_context,
    load_items,
    parse_yaml,
)

ROOT = Path.cwd()
CONFIG_PATH = ROOT / "dt-config.yaml"
CLINICAL_PATH = ROOT / "docs" / "dt-clinical-context.md"
ITEMS_DIR = ROOT / "docs" / "items"
PROMPTS_DIR = ROOT / "docs" / "generated" / "prompts"

UI_PATH_HINTS = (
    ".tsx", ".jsx", ".vue", ".svelte", "frontend/", "ui/", "web/",
    "viewer/", "frontend\\", "ui\\", "web\\", "viewer\\",
)
UI_TEXT_HINTS = (
    "user clicks", "user enters", "user sees", "user navigates",
    "screen", "page", "form", "button", "menu", "modal", "dialog",
    "viewer", "operator", "interface",
)


def _has_ui_signal(srs: Item, usc_items: list[Item]) -> bool:
    """Return True if this SRS likely has a UI surface."""
    sources = srs.fm.get("source") or []
    for s in sources:
        s_lower = str(s).lower()
        if any(h in s_lower for h in UI_PATH_HINTS):
            return True

    text = (srs.title + " " + (srs.fm.get("description") or "") + " " + srs.body).lower()
    if any(h in text for h in UI_TEXT_HINTS):
        return True

    parents = (srs.fm.get("links") or {}).get("parent") or []
    usc_ids = {u.id for u in usc_items}
    if any(p in usc_ids for p in parents):
        return True

    return False


def _orphan_srs(
    srs_items: list[Item], sds_items: list[Item], tc_items: list[Item]
) -> tuple[list[Item], list[Item]]:
    """Return (orphans_no_sds, orphans_no_tc) for Must SRS items."""
    impls_by_srs: set[str] = set()
    for sds in sds_items:
        if sds.status == "Deprecated":
            continue
        for srs_id in (sds.fm.get("links") or {}).get("implements") or []:
            impls_by_srs.add(srs_id)

    verifs_by_srs: set[str] = set()
    for tc in tc_items:
        if tc.status == "Deprecated":
            continue
        for srs_id in (tc.fm.get("links") or {}).get("verifies") or []:
            verifs_by_srs.add(srs_id)

    must_srs = [
        s for s in srs_items
        if s.status != "Deprecated"
        and (s.fm.get("priority") or "Must") == "Must"
    ]

    no_sds = [s for s in must_srs if s.id not in impls_by_srs]
    no_tc = [s for s in must_srs if s.id not in verifs_by_srs]
    return no_sds, no_tc


def _product_block(config: dict, clinical: dict[str, str]) -> str:
    """Render a short product-context block for prompt headers."""
    doc = (config.get("document") or {}) if config else {}
    prod = (config.get("product") or {}) if config else {}
    intended = clinical.get("intended-use", "").strip()
    intended_short = intended[:400].rstrip() + ("…" if len(intended) > 400 else "")
    lines = [
        "## Product context",
        "",
        f"- Document: `{doc.get('identifier') or '[TODO]'}` — {doc.get('title') or '[TODO]'}",
        f"- Suite / Application: `{prod.get('suite') or '—'}` / `{prod.get('application') or '—'}`",
        "",
    ]
    if intended:
        lines += ["**Intended use:**", "", intended_short, ""]
    return "\n".join(lines)


def _srs_block(srs: Item) -> str:
    """Render the SRS as a quotable block for the prompt body."""
    desc = srs.fm.get("description") or ""
    desc_str = desc.strip() if isinstance(desc, str) else ""
    sources = srs.fm.get("source") or []
    src_lines = [f"  - `{s}`" for s in sources] or ["  - (none — implementation gap)"]
    return (
        f"## SRS — {srs.id}\n\n"
        f"**Title:** {srs.title}\n\n"
        f"**Description:**\n\n{desc_str or '(see body below)'}\n\n"
        f"**Verification method:** `{srs.fm.get('verification') or '—'}`\n"
        f"**Priority:** `{srs.fm.get('priority') or 'Must'}`\n"
        f"**Source files referenced by the SRS:**\n" + "\n".join(src_lines) + "\n\n"
        f"**Full SRS item body:**\n\n```markdown\n{srs.body.strip()}\n```\n"
    )


# ---------------------------------------------------------------------------
# Prompt generators
# ---------------------------------------------------------------------------


def prompt_impl(srs: Item, product_block: str) -> str:
    """Generate the implementation prompt for a SRS lacking an SDS."""
    return f"""# Prompt: implement `{srs.id}`

> Ready to paste in a Claude Code session in the target repo.
> Generated by `/doc-prompts` on {date.today().isoformat()}.

{product_block}

{_srs_block(srs)}

## Task

Implement the code that satisfies `{srs.id}`. The current repo has **no
SDS item** declaring `links.implements: [{srs.id}]`, which means no
module is recorded as implementing this requirement. Your goals:

1. **Identify or write the module.** If a module already implements the
   behavior (just not linked), find it. Otherwise, write the code.
2. **Create or update the SDS item** under `docs/items/SDS/`:
   - If a suitable SDS exists, add `{srs.id}` to its
     `links.implements`, bump `version` patch, set `updated:` to today,
     and reset `status: Approved → Draft` if applicable.
   - Otherwise, create `docs/items/SDS/<NEW-ID>.md` from
     `docs/templates/sds-item.template.md`, filling the frontmatter
     (`module`, `source`, `links.implements: [{srs.id}]`) and the body
     (`## Responsibility`, `## Interfaces`, `## Invariants`,
     `## Design notes`).
3. **Add a code-level anchor.** At the entry point of the implementation,
   add a comment `// @implements {srs.id}` (TypeScript/JavaScript) or
   `# @implements {srs.id}` (Python). This helps future `code-archeologist`
   passes keep the traceability tight.
4. **Run the test suite** to make sure nothing regresses.
5. **Do not write tests in this session** — a separate prompt
   (`{srs.id}-unit-tests.md`) handles that.

## Constraints

- Respect the existing code conventions (lint, formatter, type hints).
- If the project has `CLAUDE.md` / `AGENTS.md`, follow those rules.
- Stdlib + project deps only — do not add new dependencies without
  asking the user.
- Keep the existing public API stable unless the SRS explicitly
  changes it.

## References

- Items store convention: see `docs/templates/sds-item.template.md`.
- `id_format` for new SDS IDs: read `dt-config.yaml` if present,
  otherwise use `SDS-<DOMAIN>-<NNN>` (3 segments).
- After your work, the user will run `/doc-build` to regenerate the
  aggregates and the coverage matrix.
"""


def prompt_unit(srs: Item, product_block: str) -> str:
    """Generate the unit-test prompt for a SRS lacking a TC."""
    return f"""# Prompt: write unit tests for `{srs.id}`

> Ready to paste in a Claude Code session in the target repo.
> Generated by `/doc-prompts` on {date.today().isoformat()}.

{product_block}

{_srs_block(srs)}

## Task

Write the unit tests that verify `{srs.id}`. The current repo has **no
TC item** declaring `links.verifies: [{srs.id}]`, which means no test
is recorded as verifying this requirement. Your goals:

1. **Identify the SUT (System Under Test).** Read the SDS item that
   implements this SRS (search `docs/items/SDS/` for one with
   `links.implements: [{srs.id}]`). The SDS `source:` points to the
   module(s) you must test.
2. **Write the unit tests** following the project's existing test
   framework (pytest / vitest / jest — pick the one already in use).
   Cover at least:
   - The acceptance criteria listed in the SRS body.
   - One nominal path.
   - At least one edge case or failure path per acceptance criterion.
3. **Create the TC item(s)** under `docs/items/TC/`:
   - One TC item per test function, OR a single TC item per logical
     group of related tests — your judgement.
   - Fill the frontmatter (`type: Unit`, `automated: true`, `test_id`
     in the form `<file>::<test_name>`, `source:` pointing to the test
     file, `links.verifies: [{srs.id}]`).
   - Fill the body (`## Preconditions`, `## Steps`, `## Expected results`).
4. **Add a test-level anchor.** In the test file, just above the test
   function, add a comment `// @verifies {srs.id}` (TS) or
   `# @verifies {srs.id}` (Python). The `test-evidence-collector` agent
   uses this annotation as the authoritative source on subsequent runs.
5. **Run the test suite** to confirm everything passes.
6. **Do not modify the implementation** in this session — that is the
   job of `{srs.id}-impl.md`. If you find a bug, document it (as a
   failing test marked `xfail` with a reason) and surface it to the user.

## Constraints

- One test should fail on the unmodified code only if it reveals a
  real bug — otherwise it should pass.
- No flaky tests (no real network, no real DB unless a fixture).
- Follow the project's test conventions (file location,
  fixtures, naming).

## References

- TC template: `docs/templates/tc-item.template.md`.
- `id_format` for new TC IDs: read `dt-config.yaml` or use
  `TC-<DOMAIN>-<NNN>`.
- After your work, run `/doc-build` and `/doc-stdr-export` to update
  the test description aggregate.
"""


def prompt_e2e(srs: Item, product_block: str, usc_items: list[Item]) -> str:
    """Generate the Playwright E2E prompt for a UI-surfaced SRS."""
    parents = (srs.fm.get("links") or {}).get("parent") or []
    usc_by_id = {u.id: u for u in usc_items}
    persona = environment = task = "[TODO — no parent USC linked to this SRS]"
    for p in parents:
        if p in usc_by_id:
            usc = usc_by_id[p]
            persona = str(usc.fm.get("persona") or persona)
            environment = str(usc.fm.get("environment") or environment)
            task = str(usc.fm.get("task") or task)
            break

    return f"""# Prompt: write Playwright E2E for `{srs.id}`

> Ready to paste in a Claude Code session in the target repo.
> Generated by `/doc-prompts` on {date.today().isoformat()}.
>
> This SRS was flagged as **UI-surfaced** by `build_prompts.py` — paths
> contain frontend hints (.tsx/.vue/.svelte/frontend/viewer/…) or the
> description mentions user-facing terms.

{product_block}

{_srs_block(srs)}

## Use scenario context (IEC 62366-1)

- **Persona:** {persona}
- **Environment:** {environment}
- **Task:** {task}

## Task

Write a Playwright E2E test that exercises `{srs.id}` from a real user's
perspective. Goals:

1. **Identify the UI flow.** Read the SRS body and the SDS that
   implements it. Trace from the user's first click / input down to
   the observable result on screen.
2. **Write the Playwright test.** Use the project's existing Playwright
   conventions (`playwright.config.ts`, page-object pattern if adopted,
   fixtures for test users / clinical data). The test should:
   - Cover the **nominal path** of the use scenario.
   - Cover at least **one foreseeable use error** if relevant (typo,
     missing input, double-click) — that maps to a URSK item if one
     exists.
   - Assert observable UI state (text content, role=alert, aria-busy,
     URL change) and ideally one backend side-effect (DB write, log line).
3. **Create the TC item** under `docs/items/TC/`:
   - `type: System` or `type: E2E` (use the convention of the project).
   - `automated: true`.
   - `test_id` = the Playwright spec file `::` test name.
   - `links.verifies: [{srs.id}]`.
   - If a URSK is exercised by the negative path, also add it to
     `links.mitigates`.
4. **Run the Playwright suite** to confirm the test passes.
5. **Do not write the implementation** here — `{srs.id}-impl.md`
   handles that.

## Constraints

- Use **stable selectors** (`data-testid`, `role`, `aria-label`),
  never CSS classes or text-only locators that break on i18n.
- The test must work in CI headlessly.
- No real PHI / patient data — use fixtures.
- Test duration should stay under 60 seconds.

## References

- TC template: `docs/templates/tc-item.template.md`.
- USC parent (if linked): `docs/items/USC/{parents[0] if parents else '<USC-...>'}.md`
- After your work, run `/doc-build` and `/doc-stdr-export`. Playwright
  results consumed via `test-results.json` will then populate the STDR
  status table automatically.
"""


def write_index(
    prompts_written: dict[str, list[str]],
    no_sds: list[Item],
    no_tc: list[Item],
) -> str:
    """Render an _index.md catalogue with paste-and-go links."""
    today = date.today().isoformat()
    lines = [
        f"# Prompt catalogue — {today}",
        "",
        "One file per missing implementation / test. Open the file, copy "
        "its content, paste into a fresh Claude Code session in the target "
        "repo, and let it close the gap.",
        "",
        "## Summary",
        "",
        f"- SRS without implementing SDS: **{len(no_sds)}** → impl prompts",
        f"- SRS without verifying TC: **{len(no_tc)}** → unit-test prompts",
        f"- UI-surfaced SRS: **{sum(1 for ids in prompts_written.values() if any(p.endswith('-e2e.md') for p in ids))}**"
        " → Playwright E2E prompts",
        "",
        "## Files",
        "",
    ]
    for srs_id in sorted(prompts_written.keys()):
        files = sorted(prompts_written[srs_id])
        lines.append(f"### `{srs_id}`")
        for f in files:
            lines.append(f"- [`{f}`](./{f})")
        lines.append("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate ready-to-paste prompts for every SRS without an "
            "implementing SDS or a verifying TC."
        )
    )
    parser.add_argument(
        "--cat", choices=("impl", "unit", "e2e", "all"),
        default="all",
        help="Limit the kind of prompts emitted (default: all).",
    )
    parser.add_argument(
        "--srs", type=str, default=None,
        help="Limit to a single SRS ID (debug / focused regen).",
    )
    parser.add_argument(
        "--clean", action="store_true",
        help="Remove docs/generated/prompts/ before regenerating.",
    )
    args = parser.parse_args()

    # Load inputs
    config: dict = {}
    if CONFIG_PATH.is_file():
        try:
            config = parse_yaml(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"WARN: failed to parse dt-config.yaml: {e}", file=sys.stderr)
    clinical = load_clinical_context(CLINICAL_PATH)
    srs_items = load_items("SRS", ITEMS_DIR)
    sds_items = load_items("SDS", ITEMS_DIR)
    tc_items = load_items("TC", ITEMS_DIR)
    usc_items = load_items("USC", ITEMS_DIR)

    if not srs_items:
        print("ERROR: no SRS items under docs/items/SRS/. Run /doc-62304 first.",
              file=sys.stderr)
        return 1

    no_sds, no_tc = _orphan_srs(srs_items, sds_items, tc_items)
    if args.srs:
        no_sds = [s for s in no_sds if s.id == args.srs]
        no_tc = [s for s in no_tc if s.id == args.srs]
        if not no_sds and not no_tc:
            print(f"INFO: {args.srs} is fully covered or does not exist as a Must SRS.",
                  file=sys.stderr)

    if not no_sds and not no_tc:
        print("OK: all Must SRS have both an implementing SDS and a verifying TC. "
              "No prompts to generate.", file=sys.stderr)
        return 0

    # Clean + prepare output dir
    if args.clean and PROMPTS_DIR.is_dir():
        for f in PROMPTS_DIR.glob("*.md"):
            f.unlink()
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)

    product_block = _product_block(config, clinical)
    prompts_written: dict[str, list[str]] = {}

    def _emit(srs: Item, kind: str, content: str) -> None:
        suffix = {"impl": "-impl.md", "unit": "-unit-tests.md", "e2e": "-e2e.md"}[kind]
        path = PROMPTS_DIR / f"{srs.id}{suffix}"
        path.write_text(content, encoding="utf-8")
        prompts_written.setdefault(srs.id, []).append(path.name)

    if args.cat in ("impl", "all"):
        for srs in no_sds:
            _emit(srs, "impl", prompt_impl(srs, product_block))

    if args.cat in ("unit", "all"):
        for srs in no_tc:
            _emit(srs, "unit", prompt_unit(srs, product_block))

    if args.cat in ("e2e", "all"):
        # E2E prompt only for UI-surfaced SRS that ALSO lack a TC.
        ui_orphan_tc = [s for s in no_tc if _has_ui_signal(s, usc_items)]
        for srs in ui_orphan_tc:
            _emit(srs, "e2e", prompt_e2e(srs, product_block, usc_items))

    # Index
    index_path = PROMPTS_DIR / "_index.md"
    index_path.write_text(write_index(prompts_written, no_sds, no_tc), encoding="utf-8")

    total = sum(len(v) for v in prompts_written.values())
    print(f"OK: wrote {total} prompt file(s) under {PROMPTS_DIR.relative_to(ROOT)}",
          file=sys.stderr)
    print(f"  - impl prompts:      {sum(1 for ids in prompts_written.values() for p in ids if p.endswith('-impl.md'))}",
          file=sys.stderr)
    print(f"  - unit-test prompts: {sum(1 for ids in prompts_written.values() for p in ids if p.endswith('-unit-tests.md'))}",
          file=sys.stderr)
    print(f"  - e2e prompts:       {sum(1 for ids in prompts_written.values() for p in ids if p.endswith('-e2e.md'))}",
          file=sys.stderr)
    print(str(index_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
