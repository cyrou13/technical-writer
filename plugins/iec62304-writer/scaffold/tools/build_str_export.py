#!/usr/bin/env python3
"""Build the QMS-ready STR-auto deliverable (Software Test Report — automated).

Reads:
    dt-config.yaml                       (QMS metadata)
    docs/dt-clinical-context.md          (narrative sections)
    test-results.json                    (optional — path configurable via dt-config.yaml)
    docs/items/TC/*.md                   (optional — to resolve TC titles in the report)

Writes:
    docs/export/<identifier>-<version>-STR.md
    docs/export/<identifier>-<version>-STR.docx (if pandoc + reference_docx)
    docs/export/<identifier>-<version>-str-export.log

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
)

ROOT = Path.cwd()
CONFIG_PATH = ROOT / "dt-config.yaml"
CLINICAL_PATH = ROOT / "docs" / "dt-clinical-context.md"
ITEMS_DIR = ROOT / "docs" / "items"
EXPORT_DIR = ROOT / "docs" / "export"

ALLOWED_STATUSES = {"passed", "failed", "skipped", "not_run", "manual_passed", "manual_failed"}


# ---------------------------------------------------------------------------
# Test results loading
# ---------------------------------------------------------------------------


def load_test_results(path: Path) -> dict[str, dict]:
    """Load test-results.json and return {tc_id: result_dict}."""
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


def load_run_meta(path: Path) -> dict:
    """Return top-level run metadata from test-results.json."""
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return {k: data.get(k) for k in ("run_id", "platform", "git_sha", "run_started", "run_finished")}


def compute_summary(results: dict[str, dict], tc_ids: list[str]) -> dict[str, int]:
    """Compute status counts across all TC IDs (union of known + result keys)."""
    all_ids = set(tc_ids) | set(results.keys())
    counts: dict[str, int] = {s: 0 for s in ALLOWED_STATUSES}
    counts["total"] = len(all_ids)
    for tid in all_ids:
        r = results.get(tid)
        status = (r or {}).get("status", "not_run")
        if status not in ALLOWED_STATUSES:
            status = "not_run"
        counts[status] += 1
    return counts


# ---------------------------------------------------------------------------
# BuildContext
# ---------------------------------------------------------------------------


@dataclass
class BuildContext:
    config: dict
    clinical: dict[str, str]
    tcs: list[Item]
    results: dict[str, dict]
    run_meta: dict
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
    str_title = re.sub(
        r"\bSoftware Requirements Specification\b",
        "Software Test Report (auto)",
        str(base_title),
    )
    if str_title == base_title:
        str_title = f"{base_title} — Software Test Report (auto)"
    identifier = doc.get("identifier") or "[TODO document.identifier]"
    str_identifier = re.sub(r"\bSRS\b", "STR", str(identifier))
    if str_identifier == identifier:
        str_identifier = f"{identifier}-STR"
    version_label = doc.get("version_label") or "V01"
    date = doc.get("date") or "[TODO document.date]"
    return [
        f"# {str_title}",
        "",
        f"**Document identifier:** {str_identifier}  ",
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
            "One short paragraph describing what this STR covers: the automated test run, "
            "CI platform, git revision, and overall pass/fail verdict.",
            config=ctx.config,
            root=ROOT,
        ),
        "",
        "## 1.2 Abbreviations and Glossary",
        "",
        section_with_fallback(
            ctx.clinical,
            "abbreviations",
            "List abbreviations used in this document (e.g. TC, CI, STR, SRS).",
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
        "This report is generated automatically from `test-results.json` emitted by CI. "
        "Status values: `passed`, `failed`, `skipped`, `not_run`, `manual_passed`, `manual_failed`.",
        "",
        "---",
        "",
    ]
    return lines


def build_automated_platform(ctx: BuildContext) -> list[str]:
    return [
        "# 2. Automated Tests Platform",
        "",
        section_with_fallback(
            ctx.clinical,
            "automated-tests-platform",
            "Describe the CI platform: provider (GitHub Actions / GitLab CI / Jenkins), "
            "runners, frequency, secrets management, artefact retention.",
            config=ctx.config,
            root=ROOT,
        ),
        "",
        "---",
        "",
    ]


def build_local_platforms(ctx: BuildContext) -> list[str]:
    return [
        "# 3. Local Tests Platforms",
        "",
        section_with_fallback(
            ctx.clinical,
            "local-tests-platforms",
            "Describe developer local test platforms: dev container images, local databases, "
            "mock services, IDE integrations.",
            config=ctx.config,
            root=ROOT,
        ),
        "",
        "---",
        "",
    ]


def _ids_by_status(results: dict[str, dict], tc_ids: list[str], status: str) -> list[str]:
    all_ids = sorted(set(tc_ids) | set(results.keys()))
    out = []
    for tid in all_ids:
        r = results.get(tid)
        s = (r or {}).get("status", "not_run")
        if s not in ALLOWED_STATUSES:
            s = "not_run"
        if s == status:
            out.append(tid)
    return out


def build_overview(ctx: BuildContext) -> list[str]:
    tc_ids = [t.id for t in ctx.tcs if t.status != "Deprecated"]
    tc_by_id = {t.id: t for t in ctx.tcs}
    results = ctx.results
    meta = ctx.run_meta

    lines: list[str] = [
        "# 4. Overview of Test Results",
        "",
    ]

    if not ctx.results_path.is_file():
        lines += [
            "<mark>[TODO test-results] Run CI and emit `test-results.json` to populate "
            "execution status.</mark>",
            "",
        ]
        # Still emit the table structure but all zeros
        lines += [
            "| Total | Passed | Failed | Skipped | Not run |",
            "|---|---|---|---|---|",
            "| — | — | — | — | — |",
            "",
            "---",
            "",
        ]
        return lines

    # Run metadata
    lines += [
        "## 4.1 Run metadata",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Run ID | {meta.get('run_id') or '—'} |",
        f"| Platform | {meta.get('platform') or '—'} |",
        f"| Git SHA | `{meta.get('git_sha') or '—'}` |",
        f"| Started | {meta.get('run_started') or '—'} |",
        f"| Finished | {meta.get('run_finished') or '—'} |",
        "",
    ]

    # Summary table
    summary = compute_summary(results, tc_ids)
    lines += [
        "## 4.2 Synthesis",
        "",
        "| Total | Passed | Failed | Skipped | Not run | Manual passed | Manual failed |",
        "|---|---|---|---|---|---|---|",
        f"| {summary['total']} | {summary['passed']} | {summary['failed']} "
        f"| {summary['skipped']} | {summary['not_run']} "
        f"| {summary['manual_passed']} | {summary['manual_failed']} |",
        "",
    ]

    # By-status TC ID lists
    lines.append("## 4.3 TC IDs by status")
    lines.append("")
    for status in ("passed", "failed", "skipped", "not_run", "manual_passed", "manual_failed"):
        ids = _ids_by_status(results, tc_ids, status)
        if not ids:
            continue
        lines.append(f"**{status.replace('_', ' ').title()}** ({len(ids)}): "
                     + ", ".join(f"`{i}`" for i in ids))
        lines.append("")

    # Failed detail
    failed_ids = _ids_by_status(results, tc_ids, "failed")
    if failed_ids:
        lines += [
            "## 4.4 Failed tests detail",
            "",
            "| TC ID | Description | Error | Evidence |",
            "|---|---|---|---|",
        ]
        for tid in failed_ids:
            r = results.get(tid) or {}
            tc = tc_by_id.get(tid)
            desc = tc.title if tc else "—"
            notes = str(r.get("notes") or "—").replace("|", "\\|")
            evidence = str(r.get("evidence") or "—")
            lines.append(f"| `{tid}` | {desc} | {notes} | {evidence} |")
        lines.append("")

    lines += ["---", ""]
    return lines


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def render_markdown(ctx: BuildContext) -> str:
    parts: list[str] = []
    parts += build_cover(ctx)
    parts += build_revision_history(ctx)
    parts += build_introduction(ctx)
    parts += build_automated_platform(ctx)
    parts += build_local_platforms(ctx)
    parts += build_overview(ctx)
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
        description="Build the QMS-ready STR-auto (Software Test Report) deliverable."
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

    # Load TC items (optional — for title resolution)
    tcs = load_items("TC", ITEMS_DIR)

    # Load test results
    results = load_test_results(results_path)
    run_meta = load_run_meta(results_path)
    if not results_path.is_file():
        print(f"WARN: {results_path} not found — overview will show TODO", file=sys.stderr)
    else:
        print(f"INFO: loaded {len(results)} test result(s) from {results_path}", file=sys.stderr)

    ctx = BuildContext(
        config=config,
        clinical=clinical,
        tcs=tcs,
        results=results,
        run_meta=run_meta,
        results_path=results_path,
    )

    md = render_markdown(ctx)

    # Output paths
    doc = (config.get("document") or {}) if config else {}
    identifier = str(doc.get("identifier") or "UNKNOWN").strip()
    str_identifier = re.sub(r"\bSRS\b", "STR", identifier)
    if str_identifier == identifier:
        str_identifier = f"{identifier}-STR"
    version_label = str(doc.get("version_label") or "V01").strip()

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    md_path = EXPORT_DIR / f"{str_identifier}-{version_label}-STR.md"
    docx_path = EXPORT_DIR / f"{str_identifier}-{version_label}-STR.docx"
    log_path = EXPORT_DIR / f"{str_identifier}-{version_label}-str-export.log"

    md_path.write_text(md, encoding="utf-8")
    ctx.log(f"OK: wrote {md_path.relative_to(ROOT)} ({md.count(chr(10))} lines)")

    tc_ids = [t.id for t in tcs if t.status != "Deprecated"]
    summary = compute_summary(results, tc_ids)
    todos = count_todos(md)
    ctx.log(
        f"Results: total={summary['total']} passed={summary['passed']} "
        f"failed={summary['failed']} skipped={summary['skipped']} not_run={summary['not_run']}"
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
        f"build_str_export run at {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"identifier={str_identifier} version_label={version_label}",
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
