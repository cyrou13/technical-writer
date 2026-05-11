#!/usr/bin/env python3
"""Build the QMS-ready STDR deliverable (Software Test Description and Reports).

Reads:
    dt-config.yaml                       (QMS metadata)
    docs/dt-clinical-context.md          (narrative sections)
    docs/items/TC/*.md                   (required — error if empty)
    docs/items/SRS/*.md                  (optional — used for domain grouping)
    test-results.json                    (optional — path configurable via dt-config.yaml)

Writes:
    docs/export/<identifier>-<version>-STDR.md
    docs/export/<identifier>-<version>-STDR.docx (if pandoc + reference_docx)
    docs/export/<identifier>-<version>-stdr-export.log

Stdlib only. Python 3.12+.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import (  # noqa: E402
    Item,
    load_clinical_context,
    load_items,
    parse_yaml,
    section_with_fallback,
    todo_marker,
)

ROOT = Path.cwd()
CONFIG_PATH = ROOT / "dt-config.yaml"
CLINICAL_PATH = ROOT / "docs" / "dt-clinical-context.md"
ITEMS_DIR = ROOT / "docs" / "items"
EXPORT_DIR = ROOT / "docs" / "export"

ALLOWED_STATUSES = {"passed", "failed", "skipped", "not_run", "manual_passed", "manual_failed"}

DOMAIN_PRETTY: dict[str, str] = {
    "ACQ": "Acquisition",
    "AUTH": "Authentication",
    "CAD": "Detection",
    "CFG": "Configuration",
    "EXE": "Execution",
    "IFC": "Interfaces",
    "ITR": "Image triage",
    "NET": "Networking",
    "PAY": "Payment",
    "API": "API",
}

TC_TYPE_LABELS = ("Unit", "Integration", "System", "E2E")


# ---------------------------------------------------------------------------
# Domain extraction (mirrors build_export.py logic)
# ---------------------------------------------------------------------------


def extract_domain(item_id: str) -> str:
    """Return the DOMAIN segment from an ID like <CAT>-...-<DOMAIN>-<NNN>.

    Works for 3-segment IDs (TC-AUTH-001 → AUTH) and 5-segment IDs
    (TC-CINA-CSP-ACQ-020 → ACQ). Unmatched IDs return "MISC".
    """
    m = re.match(r"^([A-Z]+)-(.+)-(\d{3})$", item_id)
    if not m:
        return "MISC"
    middle = m.group(2)
    parts = middle.split("-")
    return parts[-1]


def pretty_domain(code: str) -> str:
    return DOMAIN_PRETTY.get(code, code)


def domain_from_srs_ids(verifies: list[str]) -> str:
    """Derive domain from the first SRS ID a TC verifies."""
    for sid in verifies:
        d = extract_domain(sid)
        if d != "MISC":
            return d
    return "MISC"


# ---------------------------------------------------------------------------
# Test results loading
# ---------------------------------------------------------------------------


def load_test_results(path: Path) -> dict[str, dict]:
    """Load test-results.json and return {tc_id: result_dict}.

    Returns an empty dict if the file does not exist or cannot be parsed.
    Each result_dict contains: status, duration_seconds, analyst,
    executed_at, evidence, notes.
    """
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"WARN: could not parse {path}: {e}", file=sys.stderr)
        return {}
    results: dict[str, dict] = {}
    for entry in data.get("results") or []:
        tc_id = entry.get("tc_id")
        if not tc_id:
            continue
        results[tc_id] = entry
    return results


def run_meta(path: Path) -> dict:
    """Return top-level metadata from test-results.json (run_id, platform, etc.)."""
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return {k: data.get(k) for k in ("run_id", "platform", "git_sha", "run_started", "run_finished")}


# ---------------------------------------------------------------------------
# Summary computation
# ---------------------------------------------------------------------------


def compute_summary(tcs: list[Item], results: dict[str, dict]) -> dict[str, int]:
    counts: dict[str, int] = {"passed": 0, "failed": 0, "skipped": 0, "not_run": 0,
                               "manual_passed": 0, "manual_failed": 0, "total": len(tcs)}
    for tc in tcs:
        r = results.get(tc.id)
        status = (r or {}).get("status", "not_run")
        if status not in ALLOWED_STATUSES:
            status = "not_run"
        counts[status] = counts.get(status, 0) + 1
    return counts


def tc_status(tc: Item, results: dict[str, dict]) -> str:
    r = results.get(tc.id)
    if not r:
        return "not_run"
    s = r.get("status", "not_run")
    return s if s in ALLOWED_STATUSES else "not_run"


# ---------------------------------------------------------------------------
# BuildContext
# ---------------------------------------------------------------------------


@dataclass
class BuildContext:
    config: dict
    clinical: dict[str, str]
    tcs: list[Item]
    srs: list[Item]
    results: dict[str, dict]
    results_path: Path
    log_lines: list[str] = field(default_factory=list)

    def log(self, msg: str) -> None:
        self.log_lines.append(msg)
        print(msg, file=sys.stderr)


# ---------------------------------------------------------------------------
# Markdown builders
# ---------------------------------------------------------------------------


def fmt_signatory(ctx: BuildContext, role: str) -> str:
    approvals = (ctx.config.get("approvals") or {}) if ctx.config else {}
    entry = approvals.get(role) or {}
    name = entry.get("name") or "[TODO]"
    job = entry.get("role") or "[TODO]"
    return f"{name} — {job}"


def build_cover(ctx: BuildContext) -> list[str]:
    doc = (ctx.config.get("document") or {}) if ctx.config else {}
    base_title = doc.get("title") or "[TODO document.title]"
    # Derive STDR title
    stdr_title = re.sub(
        r"\bSoftware Requirements Specification\b",
        "Software Test Description and Reports",
        str(base_title),
    )
    if stdr_title == base_title:
        stdr_title = f"{base_title} — Software Test Description and Reports"
    identifier = doc.get("identifier") or "[TODO document.identifier]"
    stdr_identifier = re.sub(r"\bSRS\b", "STDR", str(identifier))
    if stdr_identifier == identifier:
        stdr_identifier = f"{identifier}-STDR"
    version_label = doc.get("version_label") or "V01"
    date = doc.get("date") or "[TODO document.date]"
    return [
        f"# {stdr_title}",
        "",
        f"**Document identifier:** {stdr_identifier}  ",
        f"**Version:** {version_label}  ",
        f"**Date:** {date}",
        "",
        "## Signatures",
        "",
        "| Role | Name and role | Date |",
        "|---|---|---|",
        f"| Written by | {fmt_signatory(ctx, 'written_by')} | {date} |",
        f"| Verified by | {fmt_signatory(ctx, 'verified_by')} | {date} |",
        f"| Approved by | {fmt_signatory(ctx, 'approved_by')} | {date} |",
        "",
    ]


def build_revision_history(ctx: BuildContext) -> list[str]:
    history = ctx.config.get("revision_history") or [] if ctx.config else []
    lines = ["## Revision history", "", "| Version | Date | Parts | Reason |", "|---|---|---|---|"]
    if not history:
        lines.append("| [TODO] | [TODO] | [TODO] | [TODO] |")
    else:
        for entry in history:
            if not isinstance(entry, dict):
                continue
            lines.append(
                f"| {entry.get('version') or '[TODO]'} "
                f"| {entry.get('date') or '[TODO]'} "
                f"| {entry.get('parts') or '[TODO]'} "
                f"| {entry.get('reason') or '[TODO]'} |"
            )
    lines += ["", "---", ""]
    return lines


def build_introduction(ctx: BuildContext) -> list[str]:
    refs = ctx.config.get("project_references") or [] if ctx.config else []
    lines: list[str] = [
        "# 1. Introduction",
        "",
        "## 1.1 Document overview",
        "",
        section_with_fallback(
            ctx.clinical,
            "document-overview",
            "One short paragraph describing what this STDR covers: the software item, the test lifecycle phase, and the scope.",
            config=ctx.config,
            root=ROOT,
        ),
        "",
        "## 1.2 Abbreviations and Glossary",
        "",
        section_with_fallback(
            ctx.clinical,
            "abbreviations",
            "List abbreviations used in this document (e.g. TC, SRS, CI, STDR, STR).",
            config=ctx.config,
            root=ROOT,
        ),
        "",
        "## 1.3 Project References",
        "",
    ]
    if refs:
        lines += ["| # | Document identifier | Document title |", "|---|---|---|"]
        for r in refs:
            if not isinstance(r, dict):
                continue
            label = f"[{r.get('id') or 'R?'}]"
            lines.append(
                f"| {label} | {r.get('identifier') or '[TODO]'} | {r.get('title') or '[TODO]'} |"
            )
    else:
        lines.append("_(no project references configured — edit `dt-config.yaml`)_")
    lines += [
        "",
        "## 1.4 Conventions",
        "",
        "Test case identifiers follow the format `TC-<DOMAIN>-<NNN>` (or the project-specific "
        "format configured in `dt-config.yaml`). Status values: `passed`, `failed`, `skipped`, "
        "`not_run`, `manual_passed`, `manual_failed`.",
        "",
        "---",
        "",
    ]
    return lines


def build_overview(ctx: BuildContext) -> list[str]:
    active = [t for t in ctx.tcs if t.status != "Deprecated"]
    summary = compute_summary(active, ctx.results)

    lines: list[str] = [
        "# 2. Overview of Test Results",
        "",
    ]

    if not ctx.results_path.is_file():
        lines.append(
            "<mark>[TODO test-results] Run CI tests and emit `test-results.json` to populate "
            "execution status.</mark>"
        )
        lines.append("")

    lines += [
        "## 2.1 Global summary",
        "",
        "| Total | Passed | Failed | Skipped | Not run | Manual passed | Manual failed |",
        "|---|---|---|---|---|---|---|",
        f"| {summary['total']} | {summary['passed']} | {summary['failed']} "
        f"| {summary['skipped']} | {summary['not_run']} "
        f"| {summary['manual_passed']} | {summary['manual_failed']} |",
        "",
        "## 2.2 Summary by test type",
        "",
        "| Type | Total | Passed | Failed | Skipped | Not run |",
        "|---|---|---|---|---|---|",
    ]
    for tc_type in TC_TYPE_LABELS:
        typed = [t for t in active if t.fm.get("type", "Unit") == tc_type]
        if not typed:
            continue
        s = compute_summary(typed, ctx.results)
        lines.append(
            f"| {tc_type} | {s['total']} | {s['passed']} | {s['failed']} "
            f"| {s['skipped']} | {s['not_run']} |"
        )
    lines += ["", "---", ""]
    return lines


def build_test_preparation(ctx: BuildContext) -> list[str]:
    lines: list[str] = [
        "# 3. Test Preparation",
        "",
        "## 3.1 Data preparation",
        "",
        section_with_fallback(
            ctx.clinical,
            "test-preparation-data",
            "List the test data sources: anonymised clinical datasets, synthetic data, "
            "public datasets. Reference governance and consent.",
            config=ctx.config,
            root=ROOT,
        ),
        "",
        "## 3.2 Environment preparation",
        "",
        section_with_fallback(
            ctx.clinical,
            "test-preparation-environment",
            "Describe the test environment(s): hardware specs, OS, runtime versions, "
            "test database fixtures.",
            config=ctx.config,
            root=ROOT,
        ),
        "",
        "## 3.3 Test tools",
        "",
        section_with_fallback(
            ctx.clinical,
            "test-preparation-tools",
            "List test execution tools (pytest, Vitest, Playwright, …) with versions "
            "and CI integration.",
            config=ctx.config,
            root=ROOT,
        ),
        "",
        "---",
        "",
    ]
    return lines


def _domain_for_tc(tc: Item, srs_by_id: dict[str, Item]) -> str:
    """Pick the domain from verifies links (using SRS domain) or fall back to TC ID domain."""
    verifies = list((tc.fm.get("links") or {}).get("verifies") or [])
    for sid in verifies:
        if sid in srs_by_id:
            d = extract_domain(sid)
            if d != "MISC":
                return d
    # fall back to TC's own ID domain
    d = extract_domain(tc.id)
    return d


def build_detailed_results(ctx: BuildContext) -> list[str]:
    active = [t for t in ctx.tcs if t.status != "Deprecated"]
    srs_by_id = {s.id: s for s in ctx.srs}

    # Group by domain
    by_domain: dict[str, list[Item]] = {}
    for tc in active:
        dom = _domain_for_tc(tc, srs_by_id)
        by_domain.setdefault(dom, []).append(tc)

    for dom in by_domain:
        by_domain[dom].sort(key=lambda t: t.id)

    domains_sorted = sorted(by_domain.keys())

    lines: list[str] = [
        "# 4. Detailed Test Description and Results",
        "",
    ]

    for k, dom in enumerate(domains_sorted, start=1):
        pretty = pretty_domain(dom)
        if dom not in DOMAIN_PRETTY and dom != "MISC":
            ctx.log(f"INFO: no pretty-name for domain '{dom}' — using raw code")
        lines.append(f"## 4.{k} {pretty}")
        lines.append("")

        for tc in by_domain[dom]:
            verifies = list((tc.fm.get("links") or {}).get("verifies") or [])
            preconditions = tc.fm.get("preconditions") or []
            steps = tc.fm.get("steps") or []
            expected = tc.fm.get("expected") or []

            r = ctx.results.get(tc.id) or {}
            status = r.get("status", "not_run") if r else "not_run"
            if status not in ALLOWED_STATUSES:
                status = "not_run"
            analyst = r.get("analyst") or "[TODO assign analyst]"
            executed_at = r.get("executed_at") or "—"
            evidence = r.get("evidence") or "—"
            notes = r.get("notes") or "—"

            lines += [
                f"### {tc.id}",
                "",
                f"- **Description:** {tc.title}",
                f"- **Verifies:** {', '.join(verifies) if verifies else '—'}",
            ]

            if isinstance(preconditions, list):
                prec_str = "; ".join(str(p) for p in preconditions) if preconditions else "—"
            else:
                prec_str = str(preconditions)
            lines.append(f"- **Preconditions:** {prec_str}")

            if isinstance(steps, list):
                steps_str = "; ".join(str(s) for s in steps) if steps else "—"
            else:
                steps_str = str(steps)
            lines.append(f"- **Steps:** {steps_str}")

            if isinstance(expected, list):
                exp_str = "; ".join(str(e) for e in expected) if expected else "—"
            else:
                exp_str = str(expected)
            lines.append(f"- **Expected:** {exp_str}")

            lines += [
                f"- **Status:** `{status}`",
                f"- **Analyst:** {analyst}",
                f"- **Executed at:** {executed_at}",
                f"- **Evidence:** {evidence}",
                f"- **Notes:** {notes}",
                "",
            ]

    lines += ["---", ""]
    return lines


def build_rationale(ctx: BuildContext) -> list[str]:
    return [
        "# 5. Rationale for Decisions",
        "",
        section_with_fallback(
            ctx.clinical,
            "rationale-for-decisions",
            "Document significant test design decisions: scope exclusions, sampling strategy, "
            "why certain test types were chosen.",
            config=ctx.config,
            root=ROOT,
        ),
        "",
    ]


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def render_markdown(ctx: BuildContext) -> str:
    parts: list[str] = []
    parts += build_cover(ctx)
    parts += build_revision_history(ctx)
    parts += build_introduction(ctx)
    parts += build_overview(ctx)
    parts += build_test_preparation(ctx)
    parts += build_detailed_results(ctx)
    parts += build_rationale(ctx)
    return "\n".join(parts).rstrip() + "\n"


def try_pandoc(
    md_path: Path,
    docx_path: Path,
    reference_docx: Path | None,
    ctx: BuildContext,
) -> bool:
    pandoc = shutil.which("pandoc")
    if not pandoc:
        ctx.log("INFO: pandoc not found — .docx not produced")
        return False
    cmd = [pandoc, str(md_path), "--toc", "--toc-depth=3", "-o", str(docx_path)]
    if reference_docx and reference_docx.is_file():
        cmd.insert(2, f"--reference-doc={reference_docx}")
    elif reference_docx:
        ctx.log(f"WARN: reference_docx '{reference_docx}' not found — using pandoc default style")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        ctx.log(f"WARN: pandoc failed (rc={proc.returncode}): {proc.stderr.strip()[:300]}")
        return False
    ctx.log(f"OK: wrote {docx_path.relative_to(ROOT)}")
    return True


def count_todos(md: str) -> list[str]:
    return re.findall(r"\[TODO[^\]]*\]", md)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the QMS-ready STDR (Software Test Description and Reports) deliverable."
    )
    parser.add_argument("--strict", action="store_true",
                        help="Exit 1 if [TODO] markers remain or any TC is failed.")
    parser.add_argument("--md-only", action="store_true",
                        help="Skip .docx rendering even if pandoc is available.")
    args = parser.parse_args()

    # Load config
    config: dict = {}
    if CONFIG_PATH.is_file():
        try:
            config = parse_yaml(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"ERROR: failed to parse dt-config.yaml: {e}", file=sys.stderr)
            return 1
    else:
        print("WARN: dt-config.yaml not found — using defaults with [TODO] placeholders",
              file=sys.stderr)

    # Resolve test_results_path
    tr_rel = (config.get("test_results_path") or "test-results.json") if config else "test-results.json"
    results_path = (ROOT / tr_rel).resolve()

    # Load clinical context
    clinical = load_clinical_context(CLINICAL_PATH)
    if not CLINICAL_PATH.is_file():
        print("WARN: docs/dt-clinical-context.md not found — clinical sections will be [TODO]",
              file=sys.stderr)

    # Load items
    tcs = load_items("TC", ITEMS_DIR)
    srs = load_items("SRS", ITEMS_DIR)
    if not tcs:
        print("ERROR: no TC items found under docs/items/TC/. Run /doc-62304 first.",
              file=sys.stderr)
        return 1

    # Load test results
    results = load_test_results(results_path)
    if not results_path.is_file():
        print(f"WARN: {results_path} not found — all TC will show as not_run", file=sys.stderr)
    else:
        print(f"INFO: loaded {len(results)} test result(s) from {results_path}", file=sys.stderr)

    ctx = BuildContext(
        config=config,
        clinical=clinical,
        tcs=tcs,
        srs=srs,
        results=results,
        results_path=results_path,
    )

    md = render_markdown(ctx)

    # Output paths
    doc = (config.get("document") or {}) if config else {}
    identifier = str(doc.get("identifier") or "UNKNOWN").strip()
    stdr_identifier = re.sub(r"\bSRS\b", "STDR", identifier)
    if stdr_identifier == identifier:
        stdr_identifier = f"{identifier}-STDR"
    version_label = str(doc.get("version_label") or "V01").strip()

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    md_path = EXPORT_DIR / f"{stdr_identifier}-{version_label}-STDR.md"
    docx_path = EXPORT_DIR / f"{stdr_identifier}-{version_label}-STDR.docx"
    log_path = EXPORT_DIR / f"{stdr_identifier}-{version_label}-stdr-export.log"

    md_path.write_text(md, encoding="utf-8")
    ctx.log(f"OK: wrote {md_path.relative_to(ROOT)} ({md.count(chr(10))} lines)")

    # Stats
    active = [t for t in tcs if t.status != "Deprecated"]
    summary = compute_summary(active, results)
    todos = count_todos(md)
    ctx.log(
        f"TC: {len(tcs)} total ({len(active)} active) — "
        f"passed={summary['passed']} failed={summary['failed']} "
        f"skipped={summary['skipped']} not_run={summary['not_run']}"
    )
    ctx.log(f"TODO markers in the deliverable: {len(todos)}")

    # Pandoc
    if not args.md_only:
        rendering = (config.get("rendering") or {}) if config else {}
        ref = rendering.get("reference_docx")
        ref_path = (ROOT / ref).resolve() if ref else None
        if ref_path or shutil.which("pandoc"):
            try_pandoc(md_path, docx_path, ref_path, ctx)
        else:
            ctx.log("INFO: pandoc unavailable and no reference_docx — skipping .docx")

    # Write log
    header = [
        f"build_stdr_export run at {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"identifier={stdr_identifier} version_label={version_label}",
        f"test_results_path={results_path} (found={results_path.is_file()})",
        "",
    ]
    log_path.write_text("\n".join(header + ctx.log_lines) + "\n", encoding="utf-8")
    print(str(md_path))

    # Strict gate
    if args.strict:
        problems: list[str] = []
        if todos:
            problems.append(f"{len(todos)} [TODO] marker(s) remain in the deliverable")
        if summary["failed"] > 0:
            problems.append(f"{summary['failed']} TC(s) are in failed status")
        if problems:
            print(f"STRICT: {'; '.join(problems)} — failing", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
