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

ROOT = Path.cwd()
CONFIG_PATH = ROOT / "dt-config.yaml"
CLINICAL_PATH = ROOT / "docs" / "dt-clinical-context.md"
ITEMS_DIR = ROOT / "docs" / "items"
EXPORT_DIR = ROOT / "docs" / "export"

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
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
# YAML mini-parser (indent-based, supports nested dicts, lists of dicts,
# scalars, block scalars `|`, comments). Sufficient for dt-config.yaml.
# ---------------------------------------------------------------------------


def _coerce(s: str):
    s = s.strip()
    if s == "" or s in ("null", "Null", "~"):
        return None
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    if s in ("true", "True"):
        return True
    if s in ("false", "False"):
        return False
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if re.fullmatch(r"-?\d+\.\d+", s):
        return float(s)
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1].strip()
        if not inner:
            return []
        # Preserve user placeholders like `[TODO ...]` as raw strings rather
        # than parsing them as 1-element lists.
        if "," not in inner and inner.upper().startswith("TODO"):
            return s
        return [_coerce(p) for p in inner.split(",")]
    return s


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def parse_yaml(text: str) -> dict:
    """Parse a small subset of YAML adequate for dt-config.yaml + frontmatters."""
    lines = text.splitlines()
    # Strip comments and trailing blanks while preserving line numbers logically.
    cleaned: list[str] = []
    for ln in lines:
        # Find comment marker not in a string.
        if "#" in ln:
            in_str = False
            quote = ""
            cut = -1
            for i, ch in enumerate(ln):
                if in_str:
                    if ch == quote:
                        in_str = False
                elif ch in ('"', "'"):
                    in_str = True
                    quote = ch
                elif ch == "#":
                    cut = i
                    break
            if cut >= 0:
                ln = ln[:cut].rstrip()
        cleaned.append(ln)

    pos = [0]

    def parse_block(min_indent: int):
        # Returns (value, items_consumed); inspects cleaned[pos[0]:]
        # Decides: is it a mapping (key: ...) or a sequence (- ...)?
        # Skip blank lines.
        while pos[0] < len(cleaned) and cleaned[pos[0]].strip() == "":
            pos[0] += 1
        if pos[0] >= len(cleaned):
            return None
        first = cleaned[pos[0]]
        ind = _indent(first)
        if ind < min_indent:
            return None
        if first.lstrip(" ").startswith("- "):
            return parse_sequence(ind)
        return parse_mapping(ind)

    def parse_mapping(indent: int) -> dict:
        out: dict = {}
        while pos[0] < len(cleaned):
            line = cleaned[pos[0]]
            if line.strip() == "":
                pos[0] += 1
                continue
            ind = _indent(line)
            if ind < indent:
                break
            if ind > indent:
                # Should not happen at start of mapping; bail.
                break
            m = re.match(r"^\s*([A-Za-z_][\w\-]*)\s*:\s*(.*)$", line)
            if not m:
                pos[0] += 1
                continue
            key, raw = m.group(1), m.group(2).strip()
            pos[0] += 1
            if raw == "|":
                # Block scalar
                block_lines: list[str] = []
                while pos[0] < len(cleaned):
                    nxt = cleaned[pos[0]]
                    if nxt.strip() == "":
                        block_lines.append("")
                        pos[0] += 1
                        continue
                    if _indent(nxt) <= indent:
                        break
                    block_lines.append(nxt[indent + 2 :] if len(nxt) > indent + 2 else "")
                    pos[0] += 1
                out[key] = "\n".join(block_lines).rstrip("\n")
            elif raw == "":
                # Nested mapping or sequence on next lines
                nested = parse_block(indent + 1)
                out[key] = nested if nested is not None else []
            else:
                out[key] = _coerce(raw)
        return out

    def parse_sequence(indent: int) -> list:
        out: list = []
        while pos[0] < len(cleaned):
            line = cleaned[pos[0]]
            if line.strip() == "":
                pos[0] += 1
                continue
            ind = _indent(line)
            if ind < indent:
                break
            stripped = line.lstrip(" ")
            if not stripped.startswith("- "):
                break
            after = stripped[2:]
            inline_indent = ind + 2
            if ":" in after and not after.lstrip().startswith("["):
                # Sequence of mappings — synthesize a virtual mapping line.
                # Pull the first k:v from `after`, then continue at inline_indent.
                m = re.match(r"^([A-Za-z_][\w\-]*)\s*:\s*(.*)$", after)
                if m:
                    first_key, first_raw = m.group(1), m.group(2).strip()
                    cleaned[pos[0]] = " " * inline_indent + after
                    item = parse_mapping(inline_indent)
                    out.append(item)
                    continue
            # Scalar item
            out.append(_coerce(after))
            pos[0] += 1
        return out

    result = parse_block(0)
    return result if isinstance(result, dict) else {}


# ---------------------------------------------------------------------------
# Item loading
# ---------------------------------------------------------------------------


@dataclass
class Item:
    id: str
    category: str
    path: Path
    fm: dict
    body: str

    @property
    def title(self) -> str:
        return str(self.fm.get("title") or "(untitled)")

    @property
    def status(self) -> str:
        return str(self.fm.get("status") or "Draft")

    @property
    def version(self) -> str:
        return str(self.fm.get("version") or "1.0.0")

    @property
    def parents(self) -> list[str]:
        links = self.fm.get("links") or {}
        return list(links.get("parent") or [])


def load_items(category: str) -> list[Item]:
    cat_dir = ITEMS_DIR / category
    out: list[Item] = []
    if not cat_dir.is_dir():
        return out
    for path in sorted(cat_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        m = FRONTMATTER_RE.match(text)
        if not m:
            print(f"WARN: no frontmatter in {path}", file=sys.stderr)
            continue
        try:
            fm = parse_yaml(m.group(1))
        except Exception as e:
            print(f"WARN: bad frontmatter in {path}: {e}", file=sys.stderr)
            continue
        out.append(
            Item(
                id=str(fm.get("id") or path.stem),
                category=category,
                path=path,
                fm=fm,
                body=m.group(2).strip(),
            )
        )
    return out


# ---------------------------------------------------------------------------
# Clinical context (narrative QMS sections)
# ---------------------------------------------------------------------------


CLINICAL_ANCHORS = (
    "document-overview",
    "abbreviations",
    "glossary",
    "intended-use",
    "warnings-and-precautions",
    "connected-devices",
    "personnel-and-training",
    "packaging",
)


def load_clinical_context() -> dict[str, str]:
    """Return {anchor: section_body} for every `## anchor` block in the file.

    Anchors not present return an empty string; the caller substitutes
    `[TODO <anchor>]` so the export flags missing framing.
    """
    out: dict[str, str] = {a: "" for a in CLINICAL_ANCHORS}
    if not CLINICAL_PATH.is_file():
        return out
    text = CLINICAL_PATH.read_text(encoding="utf-8")
    # Strip HTML comments.
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    # Split on H2 headers.
    chunks = re.split(r"^##\s+([\w\-]+)\s*$", text, flags=re.MULTILINE)
    # chunks[0] = preamble; then (anchor, body, anchor, body, ...)
    for i in range(1, len(chunks), 2):
        anchor = chunks[i].strip()
        body = chunks[i + 1].strip() if i + 1 < len(chunks) else ""
        if anchor in out:
            out[anchor] = body
    return out


def section_or_todo(ctx: dict[str, str], anchor: str) -> str:
    val = ctx.get(anchor, "").strip()
    return val if val else f"[TODO {anchor}]"


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

    Keeps body content as-is otherwise. If the body is empty, falls back to
    the `description:` frontmatter field.
    """
    body = item.body.strip()
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
    domains_sorted = sorted(by_domain.keys())

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
        pretty = pretty_domain(dom)
        if dom not in DOMAIN_PRETTY and dom != "MISC":
            ctx.log(f"INFO: no pretty-name for domain '{dom}' — using raw code")
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
    parts += build_appendix_deprecated(ctx)
    return "\n".join(parts).rstrip() + "\n"


def try_pandoc(md_path: Path, docx_path: Path, reference_docx: Path | None, ctx: BuildContext) -> bool:
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
    clinical = load_clinical_context()
    if not CLINICAL_PATH.is_file():
        print("WARN: docs/dt-clinical-context.md not found — clinical sections will be [TODO]", file=sys.stderr)

    # Load items
    srs = load_items("SRS")
    map_items = load_items("MAP")
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
        f"build_export run at {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"identifier={identifier} version_label={version_label}",
        "",
    ]
    log_path.write_text("\n".join(header + ctx.log_lines) + "\n", encoding="utf-8")
    print(str(md_path))

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
