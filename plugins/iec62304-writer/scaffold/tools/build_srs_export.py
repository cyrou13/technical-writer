#!/usr/bin/env python3
"""Build the QMS-ready SRS deliverable for the dossier technique.

Reads:
    dt-config.yaml                       (QMS metadata: signatories, refs, id_format)
    docs/dt-clinical-context.md          (narrative sections from QMS)
    docs/items/SRS/*.md                  (required — error if empty)
    docs/items/MAP/*.md                  (optional — upstream parent requirements)

Writes:
    docs/export/<identifier>-<version>-SRS.md
    docs/export/<identifier>-<version>-SRS.docx (if pandoc available + reference_docx set)
    docs/export/<identifier>-<version>-export.log

Stdlib only. Python 3.12+.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# Shared helpers — see tools/_lib.py
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import (  # noqa: E402
    altitude_lint,
    report_altitude_lint,
    requirement_offenders,
    Item,
    load_clinical_context,
    load_items,
    pandoc_input,
    parse_yaml,
    section_or_todo,
    strip_internal_sections,
)

ROOT = Path.cwd()
CONFIG_PATH = ROOT / "dt-config.yaml"
CLINICAL_PATH = ROOT / "docs" / "dt-clinical-context.md"
ITEMS_DIR = ROOT / "docs" / "items"
EXPORT_DIR = ROOT / "docs" / "export"

ID_SPLIT_RE = re.compile(r"^([A-Z]+)-(.+)-(\d{3})$")

DOMAIN_PRETTY = {
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


# ---------------------------------------------------------------------------
# Domain extraction from IDs
# ---------------------------------------------------------------------------


def extract_domain(item_id: str) -> str:
    """Return the DOMAIN segment from an ID matching <CAT>-...-<DOMAIN>-<NNN>.

    Works for 3-segment IDs (SRS-AUTH-001 → AUTH) and 5-segment IDs
    (SRS-CINA-CSP-ACQ-020 → ACQ). For unmatched IDs returns "MISC".
    """
    m = re.match(r"^([A-Z]+)-(.+)-(\d{3})$", item_id)
    if not m:
        return "MISC"
    middle = m.group(2)
    parts = middle.split("-")
    return parts[-1]


def pretty_domain(code: str) -> str:
    return DOMAIN_PRETTY.get(code, code)


# ---------------------------------------------------------------------------
# Item body rendering
# ---------------------------------------------------------------------------


def render_item_body(item: Item) -> str:
    """Render an SRS item body: replace H2 (## X) with H4 (#### X) to fit nesting.

    Drops the `## Notes` section (repo-internal rationale, see `_lib`). Keeps the
    rest as-is. If the body is empty, falls back to the `description:` field.
    """
    body = strip_internal_sections(item.body).strip()
    if not body:
        desc = item.fm.get("description") or ""
        if isinstance(desc, str):
            body = desc.strip()
    # Downshift H2 to H4 (so they sit under §2.2.k which is H3).
    body = re.sub(r"^##\s+", "#### ", body, flags=re.MULTILINE)
    # Downshift H3 to H5 similarly.
    body = re.sub(r"^###\s+", "##### ", body, flags=re.MULTILINE)
    return body


# ---------------------------------------------------------------------------
# Markdown builders
# ---------------------------------------------------------------------------


@dataclass
class BuildContext:
    config: dict
    clinical: dict[str, str]
    srs: list[Item]
    map_items: list[Item]
    log_lines: list[str] = field(default_factory=list)

    def log(self, msg: str) -> None:
        self.log_lines.append(msg)
        print(msg, file=sys.stderr)


def fmt_signatory(ctx: BuildContext, role: str, default_label: str) -> str:
    approvals = (ctx.config.get("approvals") or {}) if ctx.config else {}
    entry = approvals.get(role) or {}
    name = entry.get("name") or "[TODO]"
    job = entry.get("role") or "[TODO]"
    return f"{name} — {job}"


def build_cover(ctx: BuildContext) -> list[str]:
    doc = (ctx.config.get("document") or {}) if ctx.config else {}
    title = doc.get("title") or "[TODO document.title]"
    identifier = doc.get("identifier") or "[TODO document.identifier]"
    version_label = doc.get("version_label") or "V01"
    date = doc.get("date") or "[TODO document.date]"
    lines = [
        f"# {title}",
        "",
        f"**Document identifier:** {identifier}  ",
        f"**Version:** {version_label}  ",
        f"**Date:** {date}",
        "",
        "## Signatures",
        "",
        "| Role | Name and role | Date |",
        "|---|---|---|",
        f"| Written by | {fmt_signatory(ctx, 'written_by', 'Author')} | {date} |",
        f"| Verified by | {fmt_signatory(ctx, 'verified_by', 'Verifier')} | {date} |",
        f"| Approved by | {fmt_signatory(ctx, 'approved_by', 'Approver')} | {date} |",
        "",
    ]
    return lines


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
    lines.append("")
    lines.append("---")
    lines.append("")
    return lines


def build_introduction(ctx: BuildContext) -> list[str]:
    refs = ctx.config.get("project_references") or [] if ctx.config else []
    id_fmt = (ctx.config.get("id_format") or {}) if ctx.config else {}
    default_fmt = id_fmt.get("default") if isinstance(id_fmt, dict) else None
    if not default_fmt:
        default_fmt = "{CAT}-{DOMAIN}-{NNN:03d}"

    lines: list[str] = [
        "# 1. Introduction",
        "",
        "## 1.1 Document overview",
        "",
        "This Software Requirements Specification (SRS) states the functional and "
        "non-functional requirements of the software item described below, and "
        "traces each of them to the design that realises it and to the test that "
        "verifies it.",
        "",
        section_or_todo(ctx.clinical, "document-overview"),
        "",
        "## 1.2 Abbreviations and Glossary",
        "",
        "### 1.2.1 Abbreviations",
        "",
        section_or_todo(ctx.clinical, "abbreviations"),
        "",
        "### 1.2.2 Glossary",
        "",
        section_or_todo(ctx.clinical, "glossary"),
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
            lines.append(f"| {label} | {r.get('identifier') or '[TODO]'} | {r.get('title') or '[TODO]'} |")
    else:
        lines.append("_(no project references configured — edit `dt-config.yaml`)_")
    lines += [
        "",
        "## 1.4 Conventions",
        "",
        "Requirements listed in this document follow the format:",
        "",
        "```",
        default_fmt,
        "<title>",
        "<description>",
        "V<version>",
        "```",
        "",
        "where the variables are: `{CAT}` is the category (SRS, MAP, …), "
        "`{SUITE}` and `{APP}` come from `dt-config.yaml: product`, "
        "`{DOMAIN}` is a short uppercase identifier per functional area, "
        "and `{NNN}` is a zero-padded counter.",
        "",
        "---",
        "",
    ]
    return lines


def build_requirements(ctx: BuildContext) -> list[str]:
    active = [i for i in ctx.srs if i.status != "Deprecated"]
    # Group by domain.
    by_domain: dict[str, list[Item]] = {}
    for it in active:
        dom = extract_domain(it.id)
        by_domain.setdefault(dom, []).append(it)
    for dom in by_domain:
        by_domain[dom].sort(key=lambda i: i.id)
    # Order functional areas by the pipeline-logical `domain_order` in
    # dt-config.yaml (e.g. read → preprocess → AIF → deconvolution → maps).
    # Domains not listed there fall back to alphabetical, after the ordered
    # ones. Falls back to fully alphabetical when no order is configured.
    order_cfg = (ctx.config.get("domain_order") or []) if ctx.config else []
    names_cfg = (ctx.config.get("domain_names") or {}) if ctx.config else {}
    merged_names = {**DOMAIN_PRETTY, **names_cfg}
    ordered = [d for d in order_cfg if d in by_domain]
    rest = sorted(d for d in by_domain if d not in set(ordered))
    domains_sorted = ordered + rest

    lines: list[str] = ["# 2. Requirements", "", "## 2.1 Introduction", ""]
    lines += [
        "### 2.1.2 Intended use",
        "",
        section_or_todo(ctx.clinical, "intended-use"),
        "",
        "### 2.1.3 Warnings and precautions",
        "",
        section_or_todo(ctx.clinical, "warnings-and-precautions"),
        "",
        "### 2.1.4 Connected devices",
        "",
        section_or_todo(ctx.clinical, "connected-devices"),
        "",
        "## 2.2 Functionalities",
        "",
    ]
    for k, dom in enumerate(domains_sorted, start=1):
        pretty = merged_names.get(dom, dom)
        if dom not in merged_names and dom != "MISC":
            ctx.log(f"INFO: no display name for domain '{dom}' — using raw code (set domain_names in dt-config.yaml)")
        lines += [f"### 2.2.{k} {pretty}", ""]
        for it in by_domain[dom]:
            lines += [
                f"**{it.id}**",
                "",
                f"*{it.title}*",
                "",
                render_item_body(it),
                "",
                f"V{it.version}",
                "",
            ]
    lines += [
        f"## 2.{2 + len(domains_sorted) + 1} Personnel and training",
        "",
        section_or_todo(ctx.clinical, "personnel-and-training"),
        "",
        f"## 2.{2 + len(domains_sorted) + 2} Packaging",
        "",
        section_or_todo(ctx.clinical, "packaging"),
        "",
        "---",
        "",
    ]
    return lines


def build_traceability(ctx: BuildContext) -> list[str]:
    map_by_id = {m.id: m for m in ctx.map_items}
    active = [i for i in ctx.srs if i.status != "Deprecated"]
    lines = ["# 3. Requirements traceability", "", "| SRS ID | SRS Title | MAP Parent ID | MAP Title |", "|---|---|---|---|"]
    no_parent = 0
    for it in sorted(active, key=lambda i: i.id):
        parents = it.parents
        if not parents:
            lines.append(f"| {it.id} | {it.title} | (no parent) | — |")
            no_parent += 1
            continue
        map_parents = [p for p in parents if p.startswith("MAP-")]
        if not map_parents:
            lines.append(f"| {it.id} | {it.title} | (no MAP parent) | — |")
            no_parent += 1
            continue
        ids = ", ".join(map_parents)
        titles = ", ".join(map_by_id[p].title if p in map_by_id else "(unknown MAP)" for p in map_parents)
        lines.append(f"| {it.id} | {it.title} | {ids} | {titles} |")
    lines.append("")
    if no_parent:
        ctx.log(f"WARN: {no_parent} SRS item(s) have no MAP parent")
    return lines


def _flatten_config(data: object, prefix: str = "") -> list[tuple[str, object]]:
    """Flatten a nested JSON object into (dotted.key, leaf_value) rows."""
    rows: list[tuple[str, object]] = []
    if isinstance(data, dict):
        for k, v in data.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, dict):
                rows += _flatten_config(v, key)
            else:
                rows.append((key, v))
    return rows


def _fmt_config_value(v: object) -> str:
    import json

    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "null"
    if isinstance(v, (list, dict)):
        return json.dumps(v)
    return str(v)


def build_configuration(ctx: BuildContext) -> list[str]:
    """Render §4 — configuration items tracking table + default configuration.

    Driven by `dt-config.yaml: configuration.example_file` (a JSON file,
    relative to the repo root). Returns [] when the key is absent so the
    section is opt-in per product. Optional `configuration.descriptions`
    maps a dotted parameter key to a one-line description.
    """
    import json

    cfg = (ctx.config.get("configuration") or {}) if ctx.config else {}
    example_file = cfg.get("example_file")
    if not example_file:
        return []
    path = ROOT / str(example_file)
    if not path.is_file():
        ctx.log(f"WARN: configuration.example_file '{example_file}' not found — §4 skipped")
        return []
    raw = path.read_text(encoding="utf-8")
    try:
        data = json.loads(raw)
    except Exception as e:  # noqa: BLE001
        ctx.log(f"WARN: configuration.example_file is not valid JSON ({e}) — §4 skipped")
        return []

    descriptions = cfg.get("descriptions") or {}
    rows = _flatten_config(data)
    lines: list[str] = [
        "# 4. Configuration items",
        "",
        "This section tracks the configuration items that parametrise the "
        "software behaviour, with their default values, and reproduces the "
        "default configuration applied when none is supplied. The functional "
        "requirements governing configuration are specified in §2.",
        "",
        "## 4.1 Configuration items and defaults",
        "",
        "| Parameter | Default | Description |",
        "|---|---|---|",
    ]
    for key, val in rows:
        desc = str(descriptions.get(key, "")).replace("|", "\\|")
        lines.append(f"| `{key}` | `{_fmt_config_value(val)}` | {desc} |")
    lines += [
        "",
        "## 4.2 Default configuration",
        "",
        f"Default configuration (`{example_file}`):",
        "",
        "```json",
        raw.strip(),
        "```",
        "",
        "---",
        "",
    ]
    return lines


# Provisional markers get a yellow highlight in the .docx for quick review.
# pandoc's docx writer renders a bracketed span with class `.mark` as the Word
# "Highlight" style (yellow) by default — `<mark>` HTML is NOT rendered. The
# original brackets are kept visible by escaping them inside the span.
_MARKER_RE = re.compile(r"\[((?:TODO|DRAFT|GAP)\b[^\]]*)\]")


def highlight_markers(md: str) -> str:
    """Yellow-highlight every [TODO...] / [DRAFT...] / [GAP-...] marker."""
    return _MARKER_RE.sub(r"[\\[\1\\]]{.mark}", md)


def build_appendix_deprecated(ctx: BuildContext) -> list[str]:
    deprecated = [i for i in ctx.srs if i.status == "Deprecated"]
    if not deprecated:
        return []
    lines: list[str] = ["", "---", "", "# Appendix A. Deprecated requirements", ""]
    for it in sorted(deprecated, key=lambda i: i.id):
        lines += [
            f"**{it.id}**",
            "",
            f"*{it.title}*",
            "",
            render_item_body(it),
            "",
            f"V{it.version}",
            "",
        ]
    return lines


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def render_markdown(ctx: BuildContext) -> str:
    parts: list[str] = []
    parts += build_cover(ctx)
    parts += build_revision_history(ctx)
    parts += build_introduction(ctx)
    parts += build_requirements(ctx)
    parts += build_traceability(ctx)
    parts += build_configuration(ctx)
    parts += build_appendix_deprecated(ctx)
    return highlight_markers("\n".join(parts).rstrip() + "\n")


def try_pandoc(md_path: Path, docx_path: Path, reference_docx: Path | None, ctx: BuildContext) -> bool:
    pandoc = shutil.which("pandoc")
    if not pandoc:
        ctx.log("INFO: pandoc not found — .docx not produced")
        return False
    src, is_temp = pandoc_input(md_path, EXPORT_DIR / "figures", log=ctx.log)
    cmd = [pandoc, str(src), "--toc", "--toc-depth=3", "-o", str(docx_path)]
    if reference_docx and reference_docx.is_file():
        cmd.insert(2, f"--reference-doc={reference_docx}")
    elif reference_docx:
        ctx.log(f"WARN: reference_docx '{reference_docx}' not found — using pandoc default style")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    finally:
        if is_temp:
            src.unlink(missing_ok=True)
    if proc.returncode != 0:
        ctx.log(f"WARN: pandoc failed (rc={proc.returncode}): {proc.stderr.strip()[:300]}")
        return False
    ctx.log(f"OK: wrote {docx_path.relative_to(ROOT)}")
    return True


def count_todos(md: str) -> list[str]:
    return re.findall(r"\[TODO[^\]]*\]", md)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the QMS-ready SRS deliverable.")
    parser.add_argument("--strict", action="store_true", help="Exit 1 if [TODO] or unparented SRS remain.")
    parser.add_argument("--md-only", action="store_true", help="Skip .docx rendering even if pandoc is available.")
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
        print("WARN: dt-config.yaml not found — using defaults with [TODO] placeholders", file=sys.stderr)

    # Load clinical context
    clinical = load_clinical_context(CLINICAL_PATH)
    if not CLINICAL_PATH.is_file():
        print("WARN: docs/dt-clinical-context.md not found — clinical sections will be [TODO]", file=sys.stderr)

    # Load items
    srs = load_items("SRS", ITEMS_DIR)
    map_items = load_items("MAP", ITEMS_DIR)
    if not srs:
        print("ERROR: no SRS items found under docs/items/SRS/. Run /doc-62304 first.", file=sys.stderr)
        return 1

    ctx = BuildContext(config=config, clinical=clinical, srs=srs, map_items=map_items)

    # Render
    md = render_markdown(ctx)

    # Output paths
    doc = (config.get("document") or {}) if config else {}
    identifier = str(doc.get("identifier") or "UNKNOWN").strip()
    version_label = str(doc.get("version_label") or "V01").strip()
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    md_path = EXPORT_DIR / f"{identifier}-{version_label}-SRS.md"
    docx_path = EXPORT_DIR / f"{identifier}-{version_label}-SRS.docx"
    log_path = EXPORT_DIR / f"{identifier}-{version_label}-export.log"

    md_path.write_text(md, encoding="utf-8")
    ctx.log(f"OK: wrote {md_path.relative_to(ROOT)} ({md.count(chr(10))} lines)")

    # Stats
    deprecated_count = sum(1 for i in srs if i.status == "Deprecated")
    included = len(srs) - deprecated_count
    todos = count_todos(md)
    ctx.log(f"Items: {len(srs)} SRS ({included} included, {deprecated_count} deprecated), {len(map_items)} MAP")
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
        f"build_srs_export run at {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"identifier={identifier} version_label={version_label}",
        "",
    ]
    log_path.write_text("\n".join(header + ctx.log_lines) + "\n", encoding="utf-8")
    print(str(md_path))

    # Transverse rules of the dossier (skill dossier-altitude): blocking under --strict.
    if args.strict:
        offenders = altitude_lint(md, doc="SRS", extra=requirement_offenders(srs))
        if offenders:
            report_altitude_lint("SRS", offenders)
            return 1
    # Strict gate
    if args.strict:
        unparented = sum(
            1
            for i in srs
            if i.status != "Deprecated" and not [p for p in i.parents if p.startswith("MAP-")]
        )
        if todos or unparented:
            print(
                f"STRICT: {len(todos)} [TODO] marker(s), {unparented} unparented SRS — failing",
                file=sys.stderr,
            )
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
