#!/usr/bin/env python3
"""Build the QMS-ready Software Test Plan (STP) deliverable.

Reads:
    dt-config.yaml                       (QMS metadata: signatories, refs, id_format)
    docs/dt-clinical-context.md          (narrative sections from QMS)
    docs/items/TC/*.md                   (required — error exit 1 if empty)
    docs/items/SRS/*.md                  (optional — traceability)
    docs/generated/coverage.json         (optional — §3.3 / §4.1.1 coverage)

Writes:
    docs/export/<identifier>-<version>-STP.md
    docs/export/<identifier>-<version>-STP.docx  (if pandoc + reference_docx)
    docs/export/<identifier>-<version>-stp-export.log

Stdlib only. Python 3.12+.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# Shared helpers
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
COVERAGE_PATH = ROOT / "docs" / "generated" / "coverage.json"

# ---------------------------------------------------------------------------
# Hint strings for TODO markers (QMS-author-facing)
# ---------------------------------------------------------------------------

HINTS: dict[str, str] = {
    "test-environment-overview": (
        "Describe the test process: lifecycle stages, decision gates, "
        "test report distribution, traceability to releases."
    ),
    "tests-schedule-logic": (
        "Explain how tests are scheduled: pre-commit, CI on PR, nightly, "
        "pre-release, regression cadence."
    ),
    "test-tools": (
        "List HW test platforms (specs) and SW test tools "
        "(Vitest/pytest/Playwright/Locust/etc.)."
    ),
    "test-data-doc": (
        "Describe test data sources: anonymised clinical data, synthetic data, "
        "public datasets. Reference data governance."
    ),
    "test-other-materials": (
        "List any other test materials: mock services, fixtures, captured DICOM "
        "samples, calibration files."
    ),
    "test-installation": (
        "Describe test environment installation, setup and maintenance procedures."
    ),
    "tests-identification-strategy": (
        "Explain how tests are identified: from each SRS, from each risk control, "
        "from each use scenario."
    ),
    "data-recording": (
        "Describe how test results are recorded, post-processed "
        "(junit.xml aggregation, coverage report) and analysed."
    ),
    "tests-schedule": (
        "Provide the planned test schedule with dates, milestones, dependencies "
        "on releases. Update at each release."
    ),
    "qualification": (
        "State the qualification process for the test platform and personnel: "
        "ISO 13485, training requirements, audit cadence."
    ),
}


# ---------------------------------------------------------------------------
# Build context
# ---------------------------------------------------------------------------


@dataclass
class BuildContext:
    config: dict
    clinical: dict[str, str]
    tc_items: list[Item]
    srs_items: list[Item]
    coverage: dict
    log_lines: list[str] = field(default_factory=list)

    def log(self, msg: str) -> None:
        self.log_lines.append(msg)
        print(msg, file=sys.stderr)

    def swf(self, anchor: str) -> str:
        """Shorthand for section_with_fallback using this context."""
        return section_with_fallback(
            self.clinical,
            anchor,
            HINTS[anchor],
            config=self.config,
            root=ROOT,
        )


# ---------------------------------------------------------------------------
# Output path helpers
# ---------------------------------------------------------------------------


def stp_identifier(config: dict) -> str:
    """Derive the STP document identifier from dt-config.yaml document.identifier.

    If the identifier contains 'SRS', replace that segment with 'STP'.
    Otherwise, append '-STP' to the base identifier.
    """
    doc = config.get("document") or {}
    base = str(doc.get("identifier") or "UNKNOWN").strip()
    if "SRS" in base:
        return base.replace("SRS", "STP")
    return f"{base}-STP"


def version_label(config: dict) -> str:
    doc = config.get("document") or {}
    return str(doc.get("version_label") or "V01").strip()


# ---------------------------------------------------------------------------
# Cover and revision history (mirrors build_export.py pattern)
# ---------------------------------------------------------------------------


def fmt_signatory(config: dict, role: str) -> str:
    approvals = (config.get("approvals") or {}) if config else {}
    entry = approvals.get(role) or {}
    name = entry.get("name") or "[TODO]"
    job = entry.get("role") or "[TODO]"
    return f"{name} — {job}"


def build_cover(ctx: BuildContext) -> list[str]:
    doc = (ctx.config.get("document") or {}) if ctx.config else {}
    raw_title = doc.get("title") or "[TODO document.title]"
    # Replace SRS in title with STP if present
    title = raw_title.replace("SRS", "STP") if "SRS" in raw_title else f"{raw_title} — Software Test Plan"
    identifier = stp_identifier(ctx.config)
    ver = version_label(ctx.config)
    date = doc.get("date") or "[TODO document.date]"
    lines = [
        f"# {title}",
        "",
        f"**Document identifier:** {identifier}  ",
        f"**Version:** {ver}  ",
        f"**Date:** {date}",
        "",
        "## Signatures",
        "",
        "| Role | Name and role | Date |",
        "|---|---|---|",
        f"| Written by | {fmt_signatory(ctx.config, 'written_by')} | {date} |",
        f"| Verified by | {fmt_signatory(ctx.config, 'verified_by')} | {date} |",
        f"| Approved by | {fmt_signatory(ctx.config, 'approved_by')} | {date} |",
        "",
    ]
    return lines


def build_revision_history(ctx: BuildContext) -> list[str]:
    history = (ctx.config.get("revision_history") or []) if ctx.config else []
    lines = [
        "## Revision history",
        "",
        "| Version | Date | Parts | Reason |",
        "|---|---|---|---|",
    ]
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


# ---------------------------------------------------------------------------
# §1 Introduction
# ---------------------------------------------------------------------------


def build_introduction(ctx: BuildContext) -> list[str]:
    refs = (ctx.config.get("project_references") or []) if ctx.config else []
    id_fmt = (ctx.config.get("id_format") or {}) if ctx.config else {}
    default_fmt = id_fmt.get("default") if isinstance(id_fmt, dict) else None
    if not default_fmt:
        default_fmt = "{CAT}-{DOMAIN}-{NNN:03d}"

    lines: list[str] = [
        "# 1. Introduction",
        "",
        "## 1.1 Document overview",
        "",
        ctx.swf("test-environment-overview"),
        "",
        "## 1.2 Abbreviations and Glossary",
        "",
        "### 1.2.1 Abbreviations",
        "",
        section_with_fallback(
            ctx.clinical,
            "abbreviations",
            "List all abbreviations used in this document.",
            config=ctx.config,
            root=ROOT,
        ),
        "",
        "### 1.2.2 Glossary",
        "",
        section_with_fallback(
            ctx.clinical,
            "glossary",
            "Define terms specific to the testing domain.",
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
                f"| {label} | {r.get('identifier') or '[TODO]'} "
                f"| {r.get('title') or '[TODO]'} |"
            )
    else:
        lines.append("_(no project references configured — edit `dt-config.yaml`)_")
    lines += [
        "",
        "## 1.4 Conventions",
        "",
        "Test cases in this document follow the identifier format:",
        "",
        "```",
        default_fmt,
        "<title>",
        "<description>",
        "V<version>",
        "```",
        "",
        "Each test case ID has a two-digit variant counter (NN) appended; "
        "the description states what is verified; the SRS traceability column "
        "references the verified requirement.",
        "",
        "---",
        "",
    ]
    return lines


# ---------------------------------------------------------------------------
# §2 Test Environment
# ---------------------------------------------------------------------------


def build_test_environment(ctx: BuildContext) -> list[str]:
    lines: list[str] = [
        "# 2. Test Environment",
        "",
        "## 2.1 Test process",
        "",
        ctx.swf("test-environment-overview"),
        "",
        "### 2.1.1 Tests schedule logic",
        "",
        ctx.swf("tests-schedule-logic"),
        "",
        "## 2.2 Integration and factory test site",
        "",
        "### 2.2.1 Hardware test Platform and software test tools",
        "",
        ctx.swf("test-tools"),
        "",
        "### 2.2.2 Test Data and documentation",
        "",
        ctx.swf("test-data-doc"),
        "",
        "### 2.2.3 Other test materials",
        "",
        ctx.swf("test-other-materials"),
        "",
        "### 2.2.4 Installation, set-up, and maintenance",
        "",
        ctx.swf("test-installation"),
        "",
        "### 2.2.5 Personnel",
        "",
        section_with_fallback(
            ctx.clinical,
            "personnel-and-training",
            "Required user role, training and qualification level for test execution.",
            config=ctx.config,
            root=ROOT,
        ),
        "",
        "---",
        "",
    ]
    return lines


# ---------------------------------------------------------------------------
# §3 Tests Identification
# ---------------------------------------------------------------------------


def _count_by_type(tc_items: list[Item]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for t in tc_items:
        if t.status == "Deprecated":
            continue
        tc_type = str(t.fm.get("type") or "Unit")
        counts[tc_type] += 1
    return dict(counts)


def _build_phase_narrative(counts: dict[str, int]) -> str:
    """Auto-narrative: one paragraph per detected TC type."""
    if not counts:
        return "_No test cases found._"
    order = ["Unit", "Integration", "System", "E2E"]
    extra = [k for k in sorted(counts) if k not in order]
    lines: list[str] = []
    for phase in order + extra:
        n = counts.get(phase, 0)
        if n == 0:
            continue
        if phase == "Unit":
            desc = (
                f"**Unit tests** ({n} test cases) — verify individual software units "
                "in isolation. Executed on every commit via the CI pipeline."
            )
        elif phase == "Integration":
            desc = (
                f"**Integration tests** ({n} test cases) — verify interactions between "
                "software units and external interfaces. Executed on every pull request."
            )
        elif phase == "System":
            desc = (
                f"**System tests** ({n} test cases) — verify end-to-end system behaviour "
                "against SRS requirements. Executed on release candidates."
            )
        elif phase == "E2E":
            desc = (
                f"**End-to-end tests** ({n} test cases) — exercise the full system stack "
                "including UI and external services. Executed on release candidates."
            )
        else:
            desc = (
                f"**{phase} tests** ({n} test cases) — see individual test descriptions."
            )
        lines.append(desc)
        lines.append("")
    return "\n".join(lines).rstrip()


def build_tests_identification(ctx: BuildContext) -> list[str]:
    active_tc = [t for t in ctx.tc_items if t.status != "Deprecated"]
    counts = _count_by_type(ctx.tc_items)

    # §3.3 coverage from coverage.json
    cov = ctx.coverage
    if cov:
        impl_rate = cov.get("implementation_rate", None)
        verif_must = cov.get("verification_rate_must", None)
        srs_count = cov.get("srs_count", "?")
        tc_count = cov.get("tc_count", "?")
        coverage_rows = [
            "| Metric | Value |",
            "|---|---|",
            f"| Active SRS requirements | {srs_count} |",
            f"| Active test cases (TC) | {tc_count} |",
        ]
        if impl_rate is not None:
            coverage_rows.append(f"| Implementation coverage | {impl_rate:.0%} |")
        if verif_must is not None:
            coverage_rows.append(f"| Verification coverage (Must requirements) | {verif_must:.0%} |")
        orphan_tc = (cov.get("orphans") or {}).get("tc") or []
        if orphan_tc:
            coverage_rows.append(f"| TC without verified SRS | {len(orphan_tc)} |")
        coverage_section = "\n".join(coverage_rows)
    else:
        coverage_section = todo_marker(
            "coverage",
            "Run `python tools/build_docs.py` to generate coverage.json, "
            "then re-run this STP export to populate this table.",
        )

    # §3.5 id format
    id_fmt = (ctx.config.get("id_format") or {}) if ctx.config else {}
    default_fmt = id_fmt.get("default") if isinstance(id_fmt, dict) else "{CAT}-{DOMAIN}-{NNN:03d}"

    lines: list[str] = [
        "# 3. Tests Identification",
        "",
        "## 3.1 Testing phases",
        "",
        ctx.swf("tests-identification-strategy"),
        "",
        "## 3.2 Test progression",
        "",
        _build_phase_narrative(counts),
        "",
        "## 3.3 Test coverage",
        "",
        coverage_section,
        "",
        "## 3.4 Data recording, post-processing, and analysis",
        "",
        ctx.swf("data-recording"),
        "",
        "## 3.5 Test identification and content",
        "",
        f"Each test case identifier follows the project format `{default_fmt}` "
        "where the last two digits (NN) are the variant counter within a test suite. "
        "The description field states what is verified; the SRS traceability column "
        "references the verified requirement identifier.",
        "",
        "---",
        "",
    ]
    return lines


# ---------------------------------------------------------------------------
# §4 Planned Tests
# ---------------------------------------------------------------------------


def _build_coverage_table_by_domain(
    tc_items: list[Item],
    srs_items: list[Item],
    ctx: BuildContext,
) -> list[str]:
    """§4.1.1 — coverage table grouped by SRS domain (last segment before NNN)."""
    active_tc = [t for t in tc_items if t.status != "Deprecated"]
    active_srs = [s for s in srs_items if s.status != "Deprecated"]

    # Build verif_by_srs
    verif_by_srs: dict[str, list[str]] = defaultdict(list)
    for t in active_tc:
        for sid in (t.fm.get("links") or {}).get("verifies") or []:
            verif_by_srs[str(sid)].append(t.id)

    # Group SRS by domain (last uppercase segment before trailing NNN)
    def extract_domain(item_id: str) -> str:
        m = re.match(r"^([A-Z]+)-(.+)-(\d{3})$", item_id)
        if not m:
            return "MISC"
        parts = m.group(2).split("-")
        return parts[-1]

    domain_srs: dict[str, list[Item]] = defaultdict(list)
    for s in active_srs:
        domain_srs[extract_domain(s.id)].append(s)

    if not domain_srs and not active_tc:
        return [
            todo_marker(
                "coverage-table",
                "No SRS or TC items found. Add items and re-run.",
            ),
            "",
        ]

    lines: list[str] = [
        "| Domain | SRS requirements | TC count | Verification coverage |",
        "|---|---|---|---|",
    ]
    all_domains = sorted(domain_srs.keys()) if domain_srs else ["(all)"]
    for dom in all_domains:
        srs_list = domain_srs.get(dom, [])
        dom_tc: set[str] = set()
        for s in srs_list:
            for tc_id in verif_by_srs.get(s.id, []):
                dom_tc.add(tc_id)
        must_srs = [s for s in srs_list if s.fm.get("priority", "Must") == "Must"]
        must_covered = sum(1 for s in must_srs if verif_by_srs.get(s.id))
        rate_str = (
            f"{must_covered}/{len(must_srs)} ({must_covered / len(must_srs):.0%})"
            if must_srs
            else "n/a"
        )
        lines.append(
            f"| {dom} | {len(srs_list)} | {len(dom_tc)} | {rate_str} |"
        )
    lines.append("")

    if not active_srs:
        ctx.log("INFO: no SRS items — §4.1.1 domain table uses TC items only")

    return lines


def _build_planned_tests_table(tc_items: list[Item]) -> list[str]:
    """§4.1.2 — planned tests table sorted by ID, excluding Deprecated."""
    active = sorted(
        (t for t in tc_items if t.status != "Deprecated"),
        key=lambda t: t.id,
    )
    if not active:
        return ["_(no active test cases found)_", ""]

    lines: list[str] = [
        "| Identifier | Description | Requirement |",
        "|---|---|---|",
    ]
    for t in active:
        verifies = (t.fm.get("links") or {}).get("verifies") or []
        req_str = ", ".join(str(v) for v in verifies) if verifies else "—"
        lines.append(f"| {t.id} | {t.title} | {req_str} |")
    lines.append("")
    return lines


def build_planned_tests(ctx: BuildContext) -> list[str]:
    lines: list[str] = [
        "# 4. Planned Tests",
        "",
        "## 4.1 Factory tests",
        "",
        "### 4.1.1 Tests coverage",
        "",
    ]
    if ctx.coverage:
        lines += _build_coverage_table_by_domain(ctx.tc_items, ctx.srs_items, ctx)
    else:
        lines += [
            todo_marker(
                "coverage-table",
                "Run `python tools/build_docs.py` first to generate coverage.json.",
            ),
            "",
        ]

    lines += [
        "### 4.1.2 Planned tests",
        "",
    ]
    lines += _build_planned_tests_table(ctx.tc_items)
    lines += ["---", ""]
    return lines


# ---------------------------------------------------------------------------
# §5 Tests Schedule
# ---------------------------------------------------------------------------


def build_tests_schedule(ctx: BuildContext) -> list[str]:
    return [
        "# 5. Tests Schedule",
        "",
        ctx.swf("tests-schedule"),
        "",
        "---",
        "",
    ]


# ---------------------------------------------------------------------------
# §6 Qualification
# ---------------------------------------------------------------------------


def build_qualification(ctx: BuildContext) -> list[str]:
    return [
        "# 6. Qualification",
        "",
        ctx.swf("qualification"),
        "",
        "---",
        "",
    ]


# ---------------------------------------------------------------------------
# Markdown assembly
# ---------------------------------------------------------------------------


def render_markdown(ctx: BuildContext) -> str:
    parts: list[str] = []
    parts += build_cover(ctx)
    parts += build_revision_history(ctx)
    parts += build_introduction(ctx)
    parts += build_test_environment(ctx)
    parts += build_tests_identification(ctx)
    parts += build_planned_tests(ctx)
    parts += build_tests_schedule(ctx)
    parts += build_qualification(ctx)
    return "\n".join(parts).rstrip() + "\n"


# ---------------------------------------------------------------------------
# Pandoc rendering
# ---------------------------------------------------------------------------


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
        ctx.log(
            f"WARN: reference_docx '{reference_docx}' not found — using pandoc default style"
        )
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        ctx.log(
            f"WARN: pandoc failed (rc={proc.returncode}): {proc.stderr.strip()[:300]}"
        )
        return False
    ctx.log(f"OK: wrote {docx_path.relative_to(ROOT)}")
    return True


# ---------------------------------------------------------------------------
# TODO marker counting
# ---------------------------------------------------------------------------


def count_todos(md: str) -> list[str]:
    return re.findall(r"\[TODO[^\]]*\]", md)


def count_marks(md: str) -> int:
    return len(re.findall(r"<mark>", md))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the QMS-ready Software Test Plan (STP) deliverable."
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if any <mark>[TODO ...]</mark> markers remain in the output.",
    )
    parser.add_argument(
        "--md-only",
        action="store_true",
        help="Skip .docx rendering even if pandoc is available.",
    )
    args = parser.parse_args()

    # -- Config --
    config: dict = {}
    if CONFIG_PATH.is_file():
        try:
            config = parse_yaml(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"ERROR: failed to parse dt-config.yaml: {e}", file=sys.stderr)
            return 1
    else:
        print(
            "WARN: dt-config.yaml not found — using defaults with [TODO] placeholders",
            file=sys.stderr,
        )

    # -- Clinical context --
    clinical = load_clinical_context(CLINICAL_PATH)
    if not CLINICAL_PATH.is_file():
        print(
            "WARN: docs/dt-clinical-context.md not found — narrative sections will be TODO",
            file=sys.stderr,
        )

    # -- TC items (required) --
    tc_items = load_items("TC", ITEMS_DIR)
    if not tc_items:
        print(
            "ERROR: no TC items found under docs/items/TC/. "
            "Run /doc-62304 or /doc-item to create test cases first.",
            file=sys.stderr,
        )
        return 1

    # -- SRS items (optional) --
    srs_items = load_items("SRS", ITEMS_DIR)
    if not srs_items:
        print(
            "WARN: no SRS items found — §4.1.1 domain coverage table will be incomplete",
            file=sys.stderr,
        )

    # -- Coverage JSON (optional) --
    coverage: dict = {}
    if COVERAGE_PATH.is_file():
        try:
            coverage = json.loads(COVERAGE_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"WARN: failed to parse coverage.json: {e}", file=sys.stderr)
    else:
        print(
            "WARN: docs/generated/coverage.json not found — "
            "run `python tools/build_docs.py` first for coverage metrics",
            file=sys.stderr,
        )

    # Sanitize external_resources: the mini-YAML parser can return '{}' as a
    # string when the value is an empty inline mapping literal.
    if isinstance((config.get("external_resources")), str):
        config["external_resources"] = {}

    ctx = BuildContext(
        config=config,
        clinical=clinical,
        tc_items=tc_items,
        srs_items=srs_items,
        coverage=coverage,
    )

    # -- Render --
    md = render_markdown(ctx)

    # -- Output paths --
    ident = stp_identifier(config)
    ver = version_label(config)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    md_path = EXPORT_DIR / f"{ident}-{ver}-STP.md"
    docx_path = EXPORT_DIR / f"{ident}-{ver}-STP.docx"
    log_path = EXPORT_DIR / f"{ident}-{ver}-stp-export.log"

    md_path.write_text(md, encoding="utf-8")

    line_count = md.count("\n")
    ctx.log(f"OK: wrote {md_path.relative_to(ROOT)} ({line_count} lines)")

    # -- Stats --
    deprecated_tc = sum(1 for t in tc_items if t.status == "Deprecated")
    included_tc = len(tc_items) - deprecated_tc
    todos = count_todos(md)
    marks = count_marks(md)
    ctx.log(
        f"Items: {len(tc_items)} TC ({included_tc} included, {deprecated_tc} deprecated), "
        f"{len(srs_items)} SRS"
    )
    ctx.log(f"TODO markers in deliverable: {len(todos)} ({marks} highlighted)")

    # -- Pandoc --
    if not args.md_only:
        rendering = (config.get("rendering") or {}) if config else {}
        ref = rendering.get("reference_docx")
        ref_path = (ROOT / ref).resolve() if ref else None
        if ref_path or shutil.which("pandoc"):
            try_pandoc(md_path, docx_path, ref_path, ctx)
        else:
            ctx.log("INFO: pandoc unavailable and no reference_docx — skipping .docx")

    # -- Write log --
    header = [
        f"build_stp_export run at {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"identifier={ident} version_label={ver}",
        "",
    ]
    log_path.write_text("\n".join(header + ctx.log_lines) + "\n", encoding="utf-8")
    print(str(md_path))

    # -- Strict gate --
    if args.strict and marks > 0:
        print(
            f"STRICT: {marks} <mark>[TODO ...]</mark> marker(s) remain — failing",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
