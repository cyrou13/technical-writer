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

import fnmatch
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


#: Browsers puppeteer can drive when the one it downloads is absent (an npx
#: install fetches mermaid-cli but not its Chrome): without one every diagram
#: silently stays a code block in the .docx.
_SYSTEM_BROWSERS = ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")


def _puppeteer_env() -> dict[str, str]:
    """The environment of mmdc: PUPPETEER_EXECUTABLE_PATH set to a system browser
    when the caller has not set it and one is installed."""
    env = dict(os.environ)
    if not env.get("PUPPETEER_EXECUTABLE_PATH"):
        found = next((shutil.which(b) for b in _SYSTEM_BROWSERS if shutil.which(b)), None)
        if found:
            env["PUPPETEER_EXECUTABLE_PATH"] = found
    return env


def _puppeteer_config() -> str | None:
    """MERMAID_PUPPETEER_CONFIG, else tools/puppeteer.json when the repo ships one."""
    env = os.environ.get("MERMAID_PUPPETEER_CONFIG")
    if env:
        return env
    local = Path(__file__).resolve().parent / "puppeteer.json"
    return str(local) if local.is_file() else None


def render_mermaid_for_pandoc(
    md: str,
    figures_dir: Path,
    *,
    log=None,
    scale: int = 3,
) -> str | None:
    """Return `md` with every mermaid fence replaced by a rendered PNG reference.

    Returns None when there is nothing to do — no fences, or no renderer — which
    tells the caller to hand pandoc the original file. A block that fails to
    render is left as a fence; one bad diagram does not cost the others.

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
    for n, m in enumerate(blocks, 1):
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
                proc = subprocess.run(cmd, capture_output=True, text=True, env=_puppeteer_env(),
                                      timeout=MERMAID_RENDER_TIMEOUT_S)
            except subprocess.TimeoutExpired:
                _log(f"WARN: figure {n} timed out after {MERMAID_RENDER_TIMEOUT_S}s — left as a code block")
                continue
            finally:
                mmd.unlink(missing_ok=True)
            if proc.returncode != 0 or not png.is_file():
                detail = (proc.stderr or proc.stdout or "").strip().splitlines()
                reason = next((ln for ln in detail if "rror" in ln), detail[0] if detail else "no output")
                _log(f"WARN: figure {n} did not render ({reason[:200]}) — left as a code block")
                continue

        out.append(md[cursor:m.start()])
        out.append(f"![Figure {n}]({png})\n")
        cursor = m.end()
        rendered += 1

    if not rendered:
        return None

    out.append(md[cursor:])
    _log(f"OK: rendered {rendered}/{len(blocks)} mermaid diagram(s) to {figures_dir.name}/")
    return "".join(out)


def pandoc_input(md_path: Path, figures_dir: Path, *, log=None) -> tuple[Path, bool]:
    """Return (path to hand pandoc, whether it is a temporary file to delete)."""
    swapped = render_mermaid_for_pandoc(
        md_path.read_text(encoding="utf-8"), figures_dir, log=log
    )
    if swapped is None:
        return md_path, False
    tmp = md_path.with_suffix(".pandoc.md")
    tmp.write_text(swapped, encoding="utf-8")
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
# Where a deliverable is written
# ---------------------------------------------------------------------------
#
# With `submission.root` in dt-config.yaml, every exporter writes its deliverable
# straight into the numbered folder of the submission tree whose number is the
# document number (house convention: `05.Risk Management` holds `…-10-005-…`), so
# there is one copy of each document and no staging directory to keep in step.
# The build's own records (export logs, rendered diagrams) are not deliverables
# and go under docs/generated/build. Without `submission.root` everything goes to
# the exporter's fallback directory (docs/export), which is what a project with no
# submission tree, and the test suite, get.

_DOC_NUMBER_RE = re.compile(r"-\d{2}-(\d{3})(?=-)")
_SLOT_NUMBER_RE = re.compile(r"^(\d+)[. ]")


def submission_root(root: Path, config: dict | None) -> Path | None:
    """The submission tree the deliverables are written into, or None."""
    rel = str(((config or {}).get("submission") or {}).get("root") or "").strip()
    return (root / rel) if rel else None


def deliverable_dir(root: Path, config: dict | None, stem: str, fallback: Path) -> Path:
    """The folder a deliverable named `stem` is written to (created if needed).

    `submission.folders` is a list of `{match, folder}` entries (fnmatch on the
    stem), for a project whose file names do not carry a document number.
    Otherwise the folder is the numbered slot whose number is the document number
    in `stem` (`…-NN-NNN-…`). A stem that matches neither is an error rather than
    a silent fallback: a deliverable that lands outside the tree would ship
    without anything claiming it.
    """
    tree = submission_root(root, config)
    if tree is None:
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback
    for entry in ((config or {}).get("submission") or {}).get("folders") or []:
        if isinstance(entry, dict) and fnmatch.fnmatchcase(stem, str(entry.get("match") or "")):
            out = tree / str(entry.get("folder") or "")
            out.mkdir(parents=True, exist_ok=True)
            return out
    m = _DOC_NUMBER_RE.search(stem)
    if not m:
        raise ValueError(
            f"{stem}: no document number (…-NN-NNN-…) and no `submission.folders` "
            f"pattern matches it; cannot place it in {tree}")
    number = int(m.group(1))
    slots = [d for d in sorted(tree.iterdir()) if d.is_dir()
             and (sm := _SLOT_NUMBER_RE.match(d.name)) and int(sm.group(1)) == number] \
        if tree.is_dir() else []
    if len(slots) != 1:
        raise ValueError(
            f"{stem}: document number {number:03d} matches {len(slots)} folder(s) of {tree} "
            f"(expected one numbered folder; lay out the tree first)")
    return slots[0]


def build_dir(root: Path, config: dict | None, fallback: Path) -> Path:
    """Where an exporter keeps its build records (log, rendered diagrams), created if needed."""
    out = (root / "docs" / "generated" / "build") if submission_root(root, config) else fallback
    out.mkdir(parents=True, exist_ok=True)
    return out
