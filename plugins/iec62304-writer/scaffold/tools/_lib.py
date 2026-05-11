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

import re
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


def todo_marker(anchor: str, hint: str) -> str:
    """Render a yellow-highlighted TODO marker.

    Uses HTML `<mark>` which pandoc converts to the Word "Highlight"
    style (yellow background by default in .docx). Works in standalone
    Markdown viewers and in the pandoc-rendered .docx.

    Args:
        anchor: short identifier (e.g. "general-system-architecture")
        hint:   one-sentence explanation of what the QMS author should
                fill in here.

    Example:
        >>> todo_marker("class-diagram", "Insert the UML class diagram of the main software items.")
        '<mark>[TODO class-diagram] Insert the UML class diagram of the main software items.</mark>'
    """
    return f"<mark>[TODO {anchor}] {hint}</mark>"


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
