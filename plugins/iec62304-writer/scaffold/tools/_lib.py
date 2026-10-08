"""Shared helpers for the build_*.py scripts.

Contains the mini-YAML parser, the `Item` dataclass and its loader, the
clinical-context section splitter, and the ISO 14971 numeric mappings.

Why not a pip package: the plugin scaffolds these scripts INTO target
repos via /doc-init, and we want them to work without any pip install
step. `_lib.py` is copied alongside the scripts and imported via a
sys.path.insert at the top of each script.

Python 3.12+, stdlib only.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)

SEVERITY_INT = {"Negligible": 1, "Minor": 2, "Serious": 3, "Critical": 4, "Catastrophic": 5}
PROBABILITY_INT = {"Improbable": 1, "Remote": 2, "Occasional": 3, "Probable": 4, "Frequent": 5}


# ---------------------------------------------------------------------------
# YAML mini-parser — indent-based, supports nested mappings, lists of dicts,
# scalars, block scalars `|`, inline `#` comments. Sufficient for both
# dt-config.yaml and the frontmatter of every item template.
# ---------------------------------------------------------------------------


def _coerce(s: str):
    """Coerce a YAML scalar string into a Python value."""
    s = s.strip()
    if s == "" or s in ("null", "Null", "NULL", "~"):
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
    # Empty flow mapping `{}` → empty dict (not a string).
    if s == "{}":
        return {}
    return s


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _strip_inline_comment(ln: str) -> str:
    """Remove an inline `# comment` from a YAML line, respecting quoted strings.

    Examples:
        `severity: High         # comment`   → `severity: High`
        `title: "hello # world"`             → unchanged
        `# whole-line comment`               → empty
    """
    in_str = False
    quote = ""
    for i, ch in enumerate(ln):
        if in_str:
            if ch == quote:
                in_str = False
        elif ch in ('"', "'"):
            in_str = True
            quote = ch
        elif ch == "#":
            return ln[:i].rstrip()
    return ln


def parse_yaml(text: str) -> dict:
    """Parse the YAML subset used by dt-config.yaml and item frontmatters.

    Supports:
      - top-level and nested mappings (`key: value` or `key:` + indent)
      - sequences (`- value` or `- key: value` for list-of-dicts)
      - block scalars (`|`)
      - inline `#` comments (stripped, respects quoted strings)
      - the standard scalar coercion (null/bool/int/float/inline-list/string)

    Does NOT support: YAML anchors (`&`/`*`), multi-doc (`---`), tags (`!`),
    flow mappings (`{a: b}`), folded scalars (`>`).
    """
    lines = text.splitlines()
    cleaned: list[str] = [_strip_inline_comment(ln) for ln in lines]
    pos = [0]

    def parse_block(min_indent: int):
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
            if ind < indent or ind > indent:
                break
            m = re.match(r"^\s*([A-Za-z_][\w\-]*)\s*:\s*(.*)$", line)
            if not m:
                pos[0] += 1
                continue
            key, raw = m.group(1), m.group(2).strip()
            pos[0] += 1
            if raw == "|":
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
                m = re.match(r"^([A-Za-z_][\w\-]*)\s*:\s*(.*)$", after)
                if m:
                    cleaned[pos[0]] = " " * inline_indent + after
                    item = parse_mapping(inline_indent)
                    out.append(item)
                    continue
            out.append(_coerce(after))
            pos[0] += 1
        return out

    result = parse_block(0)
    return result if isinstance(result, dict) else {}


# ---------------------------------------------------------------------------
# Items
# ---------------------------------------------------------------------------


@dataclass
class Item:
    """One Markdown item under docs/items/<CATEGORY>/<ID>.md."""

    id: str
    category: str
    path: Path
    fm: dict
    body: str = ""

    def get(self, key: str, default=None):
        return self.fm.get(key, default)

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
    def mitigates(self) -> list[str]:
        links = self.fm.get("links") or {}
        return list(links.get("mitigates") or [])

    @property
    def parents(self) -> list[str]:
        links = self.fm.get("links") or {}
        return list(links.get("parent") or [])


def load_items(category: str, items_dir: Path) -> list[Item]:
    """Load every `<items_dir>/<category>/*.md` as an Item.

    Items with malformed frontmatter are skipped with a stderr warning.
    Returns items sorted by filename (which equals the id by convention).
    """
    cat_dir = items_dir / category
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
# Clinical context (narrative QMS sections inlined by /doc-srs-export and
# /doc-risk-export).
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
    "end-users",
    "characteristics-affecting-safety",
    # Usability Engineering File (IEC 62366-1 §5.1) — consumed by
    # /doc-use-export.
    "medical-purpose",
    "patient-population",
    "application-environment",
    "resource-requirements",
    # Software Design Description (§2, §3, §4) — consumed by /doc-sdd-export.
    "general-system-architecture",
    "architecture-rationale",
    "hardware-and-software-requirements",
    "processing-workflow",
    "application-workflow",
    "class-diagram",
    "error-code-standardization",
    "cots-control",
    "cots-hazards",
    "security-objectives",
    "cryptographic-functions",
    "user-authorisation",
    "penetration-testing",
    "security-conclusion",
    # Software Test Plan — consumed by /doc-stp-export.
    "test-environment-overview",
    "tests-schedule-logic",
    "test-tools",
    "test-data-doc",
    "test-other-materials",
    "test-installation",
    "tests-identification-strategy",
    "data-recording",
    "tests-schedule",
    "qualification",
    # Software Test Description and Reports — consumed by /doc-stdr-export.
    "test-preparation-environment",
    "test-preparation-tools",
    "test-preparation-data",
    "rationale-for-decisions",
    # Software Test Report — consumed by /doc-str-export.
    "automated-tests-platform",
    "local-tests-platforms",
)


def load_clinical_context(clinical_path: Path) -> dict[str, str]:
    """Return {anchor: section_body} for every `## anchor` block.

    Anchors absent from the file map to "" so the caller can substitute
    a `[TODO <anchor>]` placeholder. Unrecognized H2 anchors are silently
    ignored.
    """
    out: dict[str, str] = {a: "" for a in CLINICAL_ANCHORS}
    if not clinical_path.is_file():
        return out
    text = clinical_path.read_text(encoding="utf-8")
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    chunks = re.split(r"^##\s+([\w\-]+)\s*$", text, flags=re.MULTILINE)
    for i in range(1, len(chunks), 2):
        anchor = chunks[i].strip()
        body = chunks[i + 1].strip() if i + 1 < len(chunks) else ""
        if anchor in out:
            out[anchor] = body
    return out


def section_or_todo(ctx: dict[str, str], anchor: str) -> str:
    """Return the section body for `anchor`, or a `[TODO ...]` placeholder.

    Legacy helper kept for back-compat. New scripts should call
    `section_with_fallback()` instead — it also supports external file
    references and yellow-highlighted TODOs.
    """
    val = ctx.get(anchor, "").strip()
    return val if val else f"[TODO {anchor}]"


def with_document_approvals(config: dict | None, doc_key: str) -> dict:
    """`config` with `approvals` replaced by the signatories of document `doc_key`.

    `document_approvals.<doc_key>` (written_by / verified_by / approved_by) overrides
    the default `approvals` role by role; a document with no entry keeps the default.
    Keys are the `documents:` keys (`rar` for the risk file, `use` for the usability
    triplet).
    """
    config = dict(config or {})
    own = (config.get("document_approvals") or {}).get(doc_key) or {}
    if isinstance(own, dict) and own:
        config["approvals"] = {**(config.get("approvals") or {}), **own}
    return config


# ---------------------------------------------------------------------------
# Front matter — cover signature table and revision history (one form for all)
# ---------------------------------------------------------------------------

#: The signature table of every cover: the role in bold, the name with its function
#: under it, date and signature boxes left blank (signed on paper or in the eQMS).
COVER_COLUMNS = ("First/Last Name", "Date (MM/DD/YYYY)", "Signature")
COVER_ROLES = (("written_by", "Written by"), ("verified_by", "Verified by"), ("approved_by", "Approved by"))
_GRID_BORDER_RE = re.compile(r"^\+-+(?:\+-+)+\+$")


def cover_people(config: dict | None, role: str) -> list[tuple[str, str]]:
    """[(name, function)] signing in `role` of `approvals` (after
    `with_document_approvals`). An entry is a dict {name, role}, a list of them or a
    bare name; with nobody configured the one row is an open marker."""
    entry = ((config.get("approvals") or {}).get(role)) if config else None
    people: list[tuple[str, str]] = []
    for e in entry if isinstance(entry, list) else [entry]:
        if isinstance(e, dict):
            name, function = str(e.get("name") or "").strip(), str(e.get("role") or "").strip()
        else:
            name, function = str(e or "").strip(), ""
        if name:
            people.append((name, function))
    return people or [(f"[TODO approvals.{role}]", "")]


def _grid_table(header: list[str], rows: list[list[list[str]]]) -> list[str]:
    """A pandoc grid table: `rows` are lists of cells, a cell a list of lines (an
    empty line separates two paragraphs of the cell)."""
    n = len(header)
    widths = [max([len(header[c])] + [len(ln) for r in rows for ln in r[c]] + [3]) for c in range(n)]
    border = "+" + "+".join("-" * (w + 2) for w in widths) + "+"

    def line(cells: list[str]) -> str:
        return "|" + "|".join(f" {t.ljust(w)} " for t, w in zip(cells, widths)) + "|"

    out = [border, line(header), "+" + "+".join("=" * (w + 2) for w in widths) + "+"]
    for r in rows:
        for i in range(max(len(cell) for cell in r) or 1):
            out.append(line([cell[i] if i < len(cell) else "" for cell in r]))
        out.append(border)
    return out


def signature_table(people_by_role: list[tuple[str, list[tuple[str, str]]]]) -> list[str]:
    """The cover table from [(role label, [(name, function), ...])]: one row per
    signatory, the role label in bold on the first row of its role, the function in
    its own paragraph under the name. A grid table, so a cell holds two paragraphs."""
    rows: list[list[list[str]]] = []
    for label, people in people_by_role:
        for n, (name, function) in enumerate(people):
            rows.append([[f"**{label}**" if n == 0 else ""],
                         [name, "", function] if function else [name], [""], [""]])
    return _grid_table(["", *COVER_COLUMNS], rows) + [""]


def cover_rows(md: str) -> list[tuple[str, str, str]]:
    """[(role label, name, function)] of the first signature table of `md` (the
    reading of `signature_table`; empty when there is none)."""
    lines = md.splitlines()
    start = next((i for i, ln in enumerate(lines) if _GRID_BORDER_RE.match(ln)), None)
    if start is None:
        return []
    rows: list[tuple[str, str, str]] = []
    block: list[list[str]] = []
    header_done = False
    for line in lines[start + 1:]:
        if line.startswith("+"):
            if header_done and block:
                cols = list(zip(*block))
                label = " ".join(c for c in cols[0] if c).strip("* ")
                paras = list(cols[1])
                rows.append((label, paras[0] if paras else "", " ".join(c for c in paras[1:] if c)))
            header_done = header_done or "=" in line
            block = []
            continue
        if not line.startswith("|"):
            break
        block.append([c.strip() for c in line.strip("|").split("|")])
    return rows


def document_cover(config: dict | None, *, title: str, identifier: str, version_label: str,
                   date: str) -> list[str]:
    """The cover of every deliverable: title, identification lines, then the signature
    table (`signature_table`, one row per signatory of `approvals`). No heading above
    the table and no rule below it."""
    return [
        f"# {title}",
        "",
        f"**Document identifier:** {identifier}  ",
        f"**Version:** {version_label}  ",
        f"**Date:** {date}",
        "",
        *signature_table([(label, cover_people(config, role)) for role, label in COVER_ROLES]),
    ]


#: The revision-history header: bold, with colons; no heading above the table, no
#: rule below it.
REVISION_HISTORY_HEADER = ("| **Version:** | **Date:** | **Part(s):** | **Reason:** |", "|---|---|---|---|")


def build_revision_history(config: dict | None) -> list[str]:
    """The revision-history table that follows the cover (one form for every document)."""
    history = (config.get("revision_history") or []) if config else []
    lines = list(REVISION_HISTORY_HEADER)
    rows = [e for e in history if isinstance(e, dict)]
    if not rows:
        lines.append("| [TODO] | [TODO] | [TODO] | [TODO] |")
    for entry in rows:
        lines.append(
            f"| {entry.get('version') or '[TODO]'} | {entry.get('date') or '[TODO]'} "
            f"| {entry.get('parts') or '[TODO]'} | {entry.get('reason') or '[TODO]'} |"
        )
    return lines + [""]


# Provisional markers get a yellow highlight in the .docx for quick review. pandoc's
# docx writer renders a bracketed span with class `.mark` as the Word "Highlight"
# style; the original brackets are kept visible by escaping them inside the span.
_MARKER_HIGHLIGHT_RE = re.compile(r"\[((?:TODO|DRAFT|GAP)\b[^\]]*)\]")
_GRID_BLOCK_RE = re.compile(r"(^\+[-=:+]+\+\n(?:[|+][^\n]*\n)*)", re.M)


def highlight_markers(md: str) -> str:
    """Yellow-highlight every [TODO...] / [DRAFT...] / [GAP-...] marker. A grid table
    (the cover) is aligned by character: a marker made longer would break it, so the
    grid blocks are left as written."""
    parts = _GRID_BLOCK_RE.split(md)
    return "".join(p if i % 2 else _MARKER_HIGHLIGHT_RE.sub(r"[\\[\1\\]]{.mark}", p)
                   for i, p in enumerate(parts))


def todo_marker(anchor: str, hint: str) -> str:
    """Render a yellow-highlighted TODO marker.

    Uses a pandoc bracketed span with class `.mark`, which the pandoc docx
    writer renders as the Word "Highlight" style (yellow) by default — no
    reference-doc or extension flag required. (HTML `<mark>` is NOT rendered
    by the docx writer, so it must not be used.) The `[TODO ...]` brackets
    are kept visible by escaping them inside the span.

    Args:
        anchor: short identifier (e.g. "general-system-architecture")
        hint:   one-sentence explanation of what the QMS author should
                fill in here.

    Example:
        >>> todo_marker("class-diagram", "Insert the UML class diagram.")
        '[\\\\[TODO class-diagram\\\\] Insert the UML class diagram.]{.mark}'
    """
    safe_hint = str(hint).replace("]", "\\]")
    return f"[\\[TODO {anchor}\\] {safe_hint}]{{.mark}}"


def section_with_fallback(
    ctx: dict[str, str],
    anchor: str,
    hint: str,
    config: dict | None = None,
    root: Path | None = None,
) -> str:
    """Resolve a narrative section with a 3-level fallback:

    1. `dt-config.yaml: external_resources.<anchor>` points to a file
       (path relative to repo root) → inline its content verbatim.
    2. `docs/dt-clinical-context.md` has a `## <anchor>` section with
       non-empty body → inline that section.
    3. Otherwise → render a yellow-highlighted TODO marker with `hint`.

    Args:
        ctx:    clinical-context dict (returned by load_clinical_context)
        anchor: section anchor name (no leading `##`)
        hint:   QMS-author-facing explanation for the TODO marker
        config: dt-config dict (use None to skip external_resources lookup)
        root:   repo root for resolving relative paths (typically Path.cwd())

    Example dt-config.yaml:
        external_resources:
          general-system-architecture: docs/qms/system-architecture.md
          class-diagram: docs/qms/diagrams/class-diagram.md
    """
    # 1. External file pointer (highest priority)
    if config and root:
        external = (config.get("external_resources") or {}).get(anchor)
        if external:
            ext_path = (root / external).resolve()
            if ext_path.is_file():
                return ext_path.read_text(encoding="utf-8").strip()
            return todo_marker(
                anchor,
                f"{hint} (external file `{external}` referenced in dt-config.yaml not found)",
            )

    # 2. Inline section in dt-clinical-context.md
    val = ctx.get(anchor, "").strip()
    if val:
        return val

    # 3. Yellow TODO fallback
    return todo_marker(anchor, hint)


# ---------------------------------------------------------------------------
# Risk scoring helpers
# ---------------------------------------------------------------------------


def risk_index(sev: str | None, prob: str | None) -> int | None:
    """Return severity_int × probability_int, or None if either is unknown."""
    s = SEVERITY_INT.get(str(sev) if sev else "")
    p = PROBABILITY_INT.get(str(prob) if prob else "")
    if s is None or p is None:
        return None
    return s * p


def risk_level_from_index(idx: int | None) -> str:
    """Project a numerical risk index onto the qualitative Low/Medium/High scale."""
    if idx is None:
        return "—"
    if idx <= 4:
        return "Low"
    if idx <= 12:
        return "Medium"
    return "High"


# ---------------------------------------------------------------------------
# Mermaid figures
# ---------------------------------------------------------------------------
#
# The .md deliverables keep their diagrams as ```mermaid fences: readable in a
# browser, diffable in git, editable by the writer. pandoc has no idea what a
# mermaid fence is, so it copies the source into the .docx as a monospace code
# block and the reviewer reads `participant P as Pipeline` instead of a picture.
#
# So the fences are rendered to PNG and swapped for image references in a COPY
# of the markdown that only pandoc sees. The deliverable .md is never rewritten.
#
# Rendering needs mermaid-cli (`mmdc`). When it is absent nothing fails: the
# fences are left alone and the .docx is what it was before. Set MMDC to point
# at the binary, and MERMAID_PUPPETEER_CONFIG at a puppeteer JSON config when
# the sandbox needs one (`{"args": ["--no-sandbox"]}` is the usual case).

MERMAID_FENCE_RE = re.compile(r"^```mermaid[^\n]*\n(.*?)^```[ \t]*\n", re.S | re.M)

MERMAID_RENDER_TIMEOUT_S = 180


def _mmdc_path() -> str | None:
    return os.environ.get("MMDC") or shutil.which("mmdc")


def _puppeteer_config() -> str | None:
    """MERMAID_PUPPETEER_CONFIG, else tools/puppeteer.json when the repo ships one."""
    env = os.environ.get("MERMAID_PUPPETEER_CONFIG")
    if env:
        return env
    local = Path(__file__).resolve().parent / "puppeteer.json"
    return str(local) if local.is_file() else None


#: Text area of the A4 portrait page of the reference document, in cm: pandoc
#: shrinks a wide image to the width on its own, never a tall one to the height.
PAGE_TEXT_WIDTH_CM = 16.0
FIGURE_MAX_HEIGHT_CM = 20.0


def _figure_size(png: Path) -> str:
    """Pandoc size attribute that keeps a rendered diagram inside the page: empty
    when the image fits once pandoc has fitted its width, else a height bound."""
    try:
        with open(png, "rb") as fh:
            head = fh.read(24)
        w, h = int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")
    except OSError:
        return ""
    if not w or PAGE_TEXT_WIDTH_CM * h / w <= FIGURE_MAX_HEIGHT_CM:
        return ""
    return f"{{height={FIGURE_MAX_HEIGHT_CM:g}cm}}"


#: A figure image whose alt text is its caption ("Figure N: ...") or a mermaid fence:
#: the things a document numbers as figures, in reading order.
_FIGURE_IMAGE_RE = re.compile(r"!\[Figure\b[^\]]*\]\(")
#: The caption an exporter writes under a diagram, as its own paragraph: "Figure N:
#: title", "Figure N. title" or "Figure N — title", optionally in italics. It is taken
#: as the caption of the rendered figure (one caption, not two).
_CAPTION_PARAGRAPH_RE = re.compile(
    r"\A(?:[ \t]*\n)*[ \t]*(\*?)Figure\s+\d+\s*[.:\u2014\u2013-]\s*(.+?)\1[ \t]*(?:\n|\Z)")
_ATX_HEADING_RE = re.compile(r"^#{1,6}[ \t]+(.+?)[ \t#]*$", re.M)
_HEADING_NUMBER_RE = re.compile(r"^(?:Annex\s+[A-Z]|Appendix\s+[A-Z]|[A-Z]?\d+(?:\.\d+)*)\.?\s+")


def figure_number_at(md: str, pos: int) -> int:
    """The number of the figure that starts at `pos`: one more than the figures
    (captioned images and mermaid fences) before it in the document."""
    before = md[:pos]
    return len(_FIGURE_IMAGE_RE.findall(before)) + len(MERMAID_FENCE_RE.findall(before)) + 1


def number_figure_placeholder(md: str, placeholder: str) -> str:
    """`md` with `placeholder` replaced by the number of the first diagram that follows
    its first occurrence: an exporter that cites its own figure ("Figure {x} shows ...")
    cites it by the number it is rendered with, whatever figures precede it."""
    at = md.find(placeholder)
    if at < 0:
        return md
    fence = md.find("```mermaid", at)
    return md.replace(placeholder, str(figure_number_at(md, fence if fence >= 0 else at)))


def _figure_caption_after(md: str, pos: int) -> tuple[str, int]:
    """(caption title, end of the caption paragraph) when the paragraph following
    `pos` is a figure caption, else ("", pos)."""
    m = _CAPTION_PARAGRAPH_RE.match(md[pos:])
    if not m:
        return "", pos
    return m.group(2).strip().rstrip(".").strip(), pos + m.end()


def _heading_before(md: str, pos: int) -> str:
    """The text of the last heading before `pos`, without its section number."""
    headings = _ATX_HEADING_RE.findall(md[:pos])
    if not headings:
        return ""
    text = _HEADING_NUMBER_RE.sub("", headings[-1].strip()).strip()
    return text[:1].upper() + text[1:].lower() if text.isupper() else text


def render_mermaid_for_pandoc(
    md: str,
    figures_dir: Path,
    *,
    log=None,
    scale: int = 3,
) -> str | None:
    """Return `md` with every mermaid fence replaced by a rendered PNG reference.

    Returns None when there is nothing to do — no fences, or no renderer — which
    tells the caller to hand pandoc the original file. Each figure gets one
    caption, "Figure N: title", N counted over every figure of the document: the
    title is the caption paragraph the exporter wrote under the fence (consumed, so
    the figure is not captioned twice), else the heading of the section the diagram
    sits in. A block that fails to render is left as a fence; one bad diagram does
    not cost the others.

    PNGs are named by the SHA-1 of the diagram source, so an unchanged diagram is
    not re-rendered on the next build (mmdc costs a browser launch per figure)
    and a changed one can never collide with its own previous rendering.
    """
    def _log(msg: str) -> None:
        (log or (lambda m: print(m, file=sys.stderr)))(msg)

    blocks = list(MERMAID_FENCE_RE.finditer(md))
    if not blocks:
        return None

    mmdc = _mmdc_path()
    if not mmdc:
        _log(f"INFO: mmdc not found — {len(blocks)} mermaid diagram(s) stay as code blocks in the .docx")
        return None

    figures_dir.mkdir(parents=True, exist_ok=True)
    puppeteer_config = _puppeteer_config()

    out: list[str] = []
    cursor = 0
    rendered = 0
    for i, m in enumerate(blocks, 1):
        n = figure_number_at(md, m.start())
        source = m.group(1)
        digest = hashlib.sha1(source.encode("utf-8")).hexdigest()[:12]
        png = figures_dir / f"fig-{digest}.png"

        if not png.is_file():
            mmd = figures_dir / f"fig-{digest}.mmd"
            mmd.write_text(source, encoding="utf-8")
            cmd = [mmdc, "-i", str(mmd), "-o", str(png), "-b", "white", "-s", str(scale)]
            if puppeteer_config:
                cmd += ["-p", puppeteer_config]
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True,
                                      timeout=MERMAID_RENDER_TIMEOUT_S)
            except subprocess.TimeoutExpired:
                _log(f"WARN: figure {i} timed out after {MERMAID_RENDER_TIMEOUT_S}s — left as a code block")
                continue
            finally:
                mmd.unlink(missing_ok=True)
            if proc.returncode != 0 or not png.is_file():
                detail = (proc.stderr or proc.stdout or "").strip().splitlines()
                reason = next((ln for ln in detail if "rror" in ln), detail[0] if detail else "no output")
                _log(f"WARN: figure {i} did not render ({reason[:200]}) — left as a code block")
                continue

        title, end = _figure_caption_after(md, m.end())
        title = title or _heading_before(md, m.start()) or "Diagram"
        out.append(md[cursor:m.start()])
        out.append(f"![Figure {n}: {title}]({png}){_figure_size(png)}\n")
        cursor = end
        rendered += 1

    if not rendered:
        return None

    out.append(md[cursor:])
    _log(f"OK: rendered {rendered}/{len(blocks)} mermaid diagram(s) to {figures_dir.name}/")
    return "".join(out)


def render_hazard_contribution(value: object) -> str:
    """The OTS hazard contribution of `docs/ots.yaml` as Markdown.

    Free text is returned as written. The structured form — ``intro``, ``ways``
    (each ``failure`` / ``components`` / ``containment``) and ``note`` — reads as
    an introductory sentence, one table row per way of contributing, and the
    closing note.
    """
    if not isinstance(value, dict):
        return str(value or "").strip()

    def flat(v: object) -> str:
        return " ".join(str(v or "").split()).replace("|", "\\|")

    out = [flat(value.get("intro")), ""]
    ways = [w for w in value.get("ways") or [] if isinstance(w, dict)]
    if ways:
        out += ["| Contribution | Components | Containment |", "|---|---|---|"]
        out += ["| " + " | ".join(flat(w.get(k)) or "—" for k in ("failure", "components", "containment")) + " |"
                for w in ways]
        out.append("")
    out.append(flat(value.get("note")))
    return "\n".join(out).strip()


def load_ots_hazard_contribution(path: Path) -> str:
    """`hazard_contribution` of the OTS registry, rendered; empty when the file is
    absent or the entry is still a `[TODO …]` placeholder."""
    if not path.is_file():
        return ""
    text = render_hazard_contribution(parse_yaml(path.read_text(encoding="utf-8")).get("hazard_contribution"))
    return "" if "[TODO" in text else text


_FENCE_LINE_RE = re.compile(r"^[ \t]*(```|~~~)")
_CODE_SPAN_SPLIT_RE = re.compile(r"(`+[^`\n]*`+)")
_BARE_DOLLAR_RE = re.compile(r"(?<!\\)\$")


def escape_dollars(md: str) -> str:
    """`md` with every bare "$" escaped, outside code blocks and code spans.

    pandoc reads the text between two "$" as TeX math (`tex_math_dollars`): two
    identifiers carrying a "$" in one table (a UDI carrier, a price) merge the cells
    between them into one formula. No deliverable writes TeX, so a "$" is a dollar.
    """
    out: list[str] = []
    fence: str | None = None
    for line in md.split("\n"):
        m = _FENCE_LINE_RE.match(line)
        if fence is not None:
            if m and m.group(1) == fence:
                fence = None
            out.append(line)
            continue
        if m:
            fence = m.group(1)
            out.append(line)
            continue
        if "$" in line:
            parts = _CODE_SPAN_SPLIT_RE.split(line)
            line = "".join(p if i % 2 else _BARE_DOLLAR_RE.sub(r"\\$", p) for i, p in enumerate(parts))
        out.append(line)
    return "\n".join(out)


def pandoc_input(md_path: Path, figures_dir: Path, *, log=None) -> tuple[Path, bool]:
    """Return (path to hand pandoc, whether it is a temporary file to delete).

    The text pandoc reads has its mermaid fences rendered to captioned figures and
    its bare "$" escaped (`escape_dollars`); the deliverable .md is left as written.
    """
    original = md_path.read_text(encoding="utf-8")
    swapped = render_mermaid_for_pandoc(original, figures_dir, log=log)
    text = escape_dollars(original if swapped is None else swapped)
    if text == original:
        return md_path, False
    tmp = md_path.with_suffix(".pandoc.md")
    tmp.write_text(text, encoding="utf-8")
    return tmp, True


# ---------------------------------------------------------------------------
# Internal sections
# ---------------------------------------------------------------------------
#
# `## Notes` carries the writer's rationale: where a threshold comes from, what
# was considered and rejected, when the item was last read against the code. It
# is 40% of the SRS by volume and it is the half nobody can reconstruct two
# years later — so it stays in the item, in the repository, under version
# control. It is not part of the technical file: a reviewer reads what the
# device shall do, not the drafting history of the sentence that says so.
#
# `## Design notes` is NOT in this set. It is the architecture rationale the SDD
# renders as §3.1, a required section of that deliverable.

INTERNAL_SECTIONS = ("Notes",)


def strip_internal_sections(body: str, headers: tuple[str, ...] = INTERNAL_SECTIONS) -> str:
    """Remove the `## <header>` sections that stay in the repo, for export."""
    for header in headers:
        m = re.search(rf"^##\s+{re.escape(header)}\s*$", body, flags=re.MULTILINE)
        if not m:
            continue
        nxt = re.search(r"^##\s+", body[m.end():], flags=re.MULTILINE)
        end = m.end() + nxt.start() if nxt else len(body)
        body = (body[: m.start()].rstrip() + "\n\n" + body[end:].lstrip()).strip()
    return body


# ---------------------------------------------------------------------------
# Altitude lint — the transverse rules of the dossier (skill dossier-altitude)
# ---------------------------------------------------------------------------
#
# A deliverable is read by a reviewer, not by a developer. Outside a generated
# annex the body names no code (T1): no code span, no repository path, no test
# name, no configuration key, no TODO. Each field stays within its word cap
# (T3): a requirement 30–80 words; a test card's free text (description and
# expected result) ≤ 90 words with the expected result ≤ 40; a cell of the design
# risk register per its cap. No evidence list sits in a body (T4): evidence goes
# to a generated annex. A document outside the verification chain names no
# identifier of the item store (T5). The exporters run it under --strict.

#: Documents outside the verification chain (T5), by the `doc` tag the exporter passes.
NON_VERIFICATION_DOCS = frozenset({
    "SUM", "USER-GUIDE", "UEF", "USE", "INTEGRATION-GUIDE", "DICOM-CS", "LABELS",
    "MODEL-CARD", "LIFETIME", "DECLARATION", "FDA-510K",
})

#: Between these two lines the code-in-text, evidence-list and internal-id rules do
#: not read (a generated annex: a run identity, an inventory rendered from a lock, a
#: checklist evidence column). Markers are still refused there. HTML comments: the
#: exporter removes them with `strip_lint_pragmas` before writing.
GENERATED_ANNEX_BEGIN = "<!-- release-lint: generated annex -->"
GENERATED_ANNEX_END = "<!-- release-lint: end generated annex -->"

_OPEN_MARKER_RE = re.compile(r"\[(?:TODO|DRAFT|GAP-)|\bTODO\b")
_MARKER_SPAN_RE = re.compile(r"\[\\\[(?:TODO|DRAFT|GAP-).*?\]\{\.mark\}|\\?\[(?:TODO|DRAFT|GAP-)[^\]]*\]")
_INTERNAL_ID_RE = re.compile(r"\b(?:SRS|SDS|TC|RSK|URSK|PRSK|USC|THR|MAP)-[A-Z0-9]+(?:-[A-Z0-9]+)+\b")
_CODE_SPAN_RE = re.compile(r"`[^`\n]+`")
_TEST_NAME_RE = re.compile(r"\btest_[a-z0-9_]{3,}\b|::[A-Za-z_]\w*")
_PY_PATH_RE = re.compile(r"(?<![\w/.-])[A-Za-z_][\w.-]*(?:/[\w.-]+)*\.py\b")
_REPO_REL_PATH_RE = re.compile(
    r"(?<![\w/.-])(?:src|app|lib|tests|tools|scripts|docs|prod|static|submission)/[\w./@+…-]*")
_ABS_PATH_RE = re.compile(r"(?<![\w.])/(?:data\d*|home|tmp|mnt|srv|root|Users)/[\w./@+-]+")
_CONFIG_KEY_RE = re.compile(r"(?<![\w./@#-])[a-z][a-z0-9]*(?:_[a-z0-9]+)+(?![\w/(-])")
_NUMBERED_LABEL_RE = re.compile(r"[a-z]+(?:_\d+)+")
_ADDRESS_RE = re.compile(r"\]\([^)]*\)|<https?://[^>]*>|https?://\S+|[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_LIST_OR_ROW_RE = re.compile(r"^\s*(?:[-*+]\s|\d+[.)]\s|\|)")
EVIDENCE_LIST_MIN_LINES = 3


def strip_lint_pragmas(md: str) -> str:
    """The deliverable without the lint pragmas: they steer the lint, they are not text."""
    return "\n".join(ln for ln in md.split("\n") if ln.strip() not in (GENERATED_ANNEX_BEGIN, GENERATED_ANNEX_END))


def _code_in_text(line: str) -> list[tuple[str, str]]:
    text = _ADDRESS_RE.sub(" ", _MARKER_SPAN_RE.sub(" ", line))
    # A code span is refused as such; what it carries is read too.
    out = [("code-span", m.group(0)[:60]) for m in _CODE_SPAN_RE.finditer(text)]
    plain = text.replace("`", " ")
    out += [("repo-path", m.group(0)) for m in _ABS_PATH_RE.finditer(plain)]
    py_spans = [m.span() for m in _PY_PATH_RE.finditer(plain)]
    out += [("code-path", plain[a:b]) for a, b in py_spans]
    for m in _REPO_REL_PATH_RE.finditer(plain):
        a, b = m.start(), m.start() + len(m.group(0).rstrip("."))
        if not any(a < pb and pa < b for pa, pb in py_spans):
            out.append(("code-path", plain[a:b]))
    out += [("test-name", m.group(0)) for m in _TEST_NAME_RE.finditer(plain)]
    out += [("config-key", m.group(0)) for m in _CONFIG_KEY_RE.finditer(plain)
            if not m.group(0).startswith("test_") and not _NUMBERED_LABEL_RE.fullmatch(m.group(0))]
    return out


def _names_evidence(line: str) -> bool:
    text = _ADDRESS_RE.sub(" ", _MARKER_SPAN_RE.sub(" ", line))
    return bool(_TEST_NAME_RE.search(text) or _PY_PATH_RE.search(text) or _REPO_REL_PATH_RE.search(text))


def altitude_lint(body_md: str, *, doc: str, extra: list[str] | None = None) -> list[str]:
    """Every offender of the transverse rules in a deliverable body, as `kind: detail`.

    Kinds: marker, code-span, code-path, repo-path, test-name, config-key,
    evidence-list, internal-id (T1/T4/T5); `word-cap` (T3) comes through `extra`
    from `requirement_offenders`, `test_card_offenders` and `risk_cell_offenders`.
    Fenced blocks and generated annexes are not read by the code rules.
    """
    out: list[str] = []
    in_fence = annex = False
    run: list[int] = []
    user_facing = doc.upper() in NON_VERIFICATION_DOCS

    def close_run() -> None:
        if len(run) >= EVIDENCE_LIST_MIN_LINES:
            out.append(f"evidence-list: lines {run[0]}-{run[-1]}: {len(run)} entries naming tests or code")
        run.clear()

    for n, line in enumerate(body_md.splitlines(), 1):
        for m in _OPEN_MARKER_RE.finditer(line):
            out.append(f"marker: line {n}: {line[m.start():m.start() + 60].strip()}")
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if line.strip() == GENERATED_ANNEX_BEGIN:
            annex = True
            close_run()
            continue
        if line.strip() == GENERATED_ANNEX_END:
            annex = False
            continue
        if in_fence or annex:
            continue
        for kind, term in _code_in_text(line):
            out.append(f"{kind}: line {n}: {term}")
        if _LIST_OR_ROW_RE.match(line) and _names_evidence(line):
            run.append(n)
        else:
            close_run()
        if user_facing:
            for m in _INTERNAL_ID_RE.finditer(line):
                out.append(f"internal-id: line {n}: {m.group(0)}")
    close_run()
    return out + list(extra or [])


# Word caps per field (T3) ---------------------------------------------------

REQUIREMENT_MIN_WORDS, REQUIREMENT_MAX_WORDS = 30, 80
TEST_CARD_MAX_WORDS, TEST_CARD_EXPECTED_MAX_WORDS = 90, 40
#: A cell of the design risk register: field → (min, max) words.
RISK_CELL_CAPS: dict[str, tuple[int, int]] = {
    "hazard": (1, 8),
    "initiating_causes": (1, 20),
    "foreseeable_sequence": (1, 25),
    "hazardous_situation": (1, 15),
    "control_measure": (30, 60),
}
_RISK_CELL_SECTIONS = {
    "hazard": "Hazard", "initiating_causes": "Initiating causes",
    "foreseeable_sequence": "Foreseeable sequence of events", "hazardous_situation": "Hazardous situation",
    "use_error": "Use error",
}
#: The capped cells of each register — design, production and use-related risks
#: alike: field of the record → the cap of RISK_CELL_CAPS it takes. A use error
#: lands in the foreseeable-sequence column of the risk table and takes its cap; a
#: use-related risk has no initiating-cause cell and no control-measure text (its
#: controls are the linked items).
RISK_CELL_FIELDS: dict[str, dict[str, str]] = {
    "RSK": {f: f for f in RISK_CELL_CAPS},
    "PRSK": {f: f for f in RISK_CELL_CAPS},
    "URSK": {"hazard": "hazard", "use_error": "foreseeable_sequence",
             "hazardous_situation": "hazardous_situation"},
}
_ENUMERATOR_RE = re.compile(r"\(?\d+[.)]|[-*+→—–]")
_DRAFT_SPAN_RE = re.compile(r"\[(?:DRAFT|TODO)[^\]]*\]")


def word_count(text: object) -> int:
    """Words of a field; bullets, enumerators and open DRAFT/TODO markers are not words."""
    clean = _DRAFT_SPAN_RE.sub(" ", str(text or ""))
    return sum(1 for tok in clean.split()
               if re.search(r"[A-Za-z0-9]", tok) and not _ENUMERATOR_RE.fullmatch(tok))


def body_section(body: str, header: str) -> str:
    """The text of `## <header>` in an item body ("" when absent)."""
    m = re.search(rf"^##\s+{re.escape(header)}\s*$", body, flags=re.MULTILINE)
    if not m:
        return ""
    nxt = re.search(r"^##\s+", body[m.end():], flags=re.MULTILINE)
    return body[m.end(): m.end() + nxt.start() if nxt else len(body)].strip()


def _active(item: Item) -> bool:
    return item.status not in ("Deprecated", "Retired")


def requirement_offenders(items: list[Item]) -> list[str]:
    """Requirement statements (`## Description`) outside 30–80 words, kind `word-cap`."""
    out: list[str] = []
    for it in sorted(items, key=lambda i: i.id):
        if not _active(it) or str(it.get("kind") or "") == "process":
            continue
        n = word_count(body_section(it.body, "Description") or it.body)
        if not REQUIREMENT_MIN_WORDS <= n <= REQUIREMENT_MAX_WORDS:
            out.append(f"word-cap: {it.id} statement: {n} words "
                       f"(cap {REQUIREMENT_MIN_WORDS}–{REQUIREMENT_MAX_WORDS})")
    return out


def test_card_offenders(tcs: list[Item]) -> list[str]:
    """Test cards above their cap, kind `word-cap`: the free text only (description and
    expected result); the form labels, requirement ids and result line are the frame."""
    out: list[str] = []
    for tc in sorted(tcs, key=lambda i: i.id):
        if not _active(tc):
            continue
        description = (str(tc.get("objective") or "").strip() or body_section(tc.body, "Description")
                       or tc.title)
        expected = word_count(tc.get("acceptance") or body_section(tc.body, "Expected results"))
        total = word_count(description) + expected
        if expected > TEST_CARD_EXPECTED_MAX_WORDS:
            out.append(f"word-cap: {tc.id} expected: {expected} words (cap {TEST_CARD_EXPECTED_MAX_WORDS})")
        if total > TEST_CARD_MAX_WORDS:
            out.append(f"word-cap: {tc.id} card: {total} words (cap {TEST_CARD_MAX_WORDS})")
    return out


def control_measure_text(item: Item) -> str:
    """The first paragraph of `## Risk controls`, without a "Chosen hierarchy" lead sentence."""
    section = body_section(strip_internal_sections(item.body), "Risk controls")
    first = section.split("\n\n")[0] if section else ""
    return re.sub(r"^Chosen hierarchy:\s*\*\*[^*]+\*\*\.\s*", "", first).strip()


def risk_cell_offenders(items: list[Item]) -> list[str]:
    """Risk-table cells outside their cap on the design, production and use-related
    registers (RSK, PRSK, URSK), kind `word-cap`."""
    out: list[str] = []
    for it in sorted(items, key=lambda i: i.id):
        fields = RISK_CELL_FIELDS.get(it.category)
        if not fields or not _active(it):
            continue
        for field, cap in fields.items():
            lo, hi = RISK_CELL_CAPS[cap]
            if field == "control_measure":
                text = control_measure_text(it)
            else:
                text = it.fm.get(field) or body_section(it.body, _RISK_CELL_SECTIONS[field])
            n = word_count(text)
            if not lo <= n <= hi:
                out.append(f"word-cap: {it.id} {field}: {n} words (cap {lo}–{hi})")
    return out


def report_altitude_lint(doc: str, offenders: list[str]) -> None:
    """Print the offenders of `altitude_lint` on stderr, counts by kind first."""
    counts: dict[str, int] = {}
    for o in offenders:
        counts[o.split(":", 1)[0]] = counts.get(o.split(":", 1)[0], 0) + 1
    print(f"ALTITUDE LINT — {doc}: {len(offenders)} offender(s): "
          + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())), file=sys.stderr)
    for o in offenders:
        print(f"  - {o}", file=sys.stderr)
