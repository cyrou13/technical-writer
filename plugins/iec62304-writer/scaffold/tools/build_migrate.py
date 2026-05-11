#!/usr/bin/env python3
"""Migration audit helper — compares a target repo against the current plugin scaffold.

Produces a migration report covering:
  A. dt-config.yaml   — top-level keys present in scaffold but absent from user config
  B. dt-clinical-context.md — H2 anchors present in scaffold but absent from user file
  C. Items frontmatter — fields present in template but absent from existing items (read-only)
  D. tools/build_*.py — missing or potentially outdated scripts

Usage:
    python tools/build_migrate.py [--apply] [--stdout]

    (no flags)  Dry-run: write report to docs/generated/migration-report.md
    --apply     Execute additive changes (sections A and B) after preview
    --stdout    Print report to stdout instead of writing to file

Scaffold path resolution (in order):
    1. $CLAUDE_PLUGIN_ROOT environment variable
    2. $IEC62304_PLUGIN_ROOT environment variable
    3. ~/.claude/plugins/iec62304-writer/

Python 3.12+, stdlib only.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap — resolve _lib.py from the target repo's tools/ directory
# (this script lives in tools/ after /doc-init copies it there)
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import FRONTMATTER_RE, parse_yaml  # noqa: E402  (after sys.path mutation)


# ---------------------------------------------------------------------------
# Scaffold path resolution
# ---------------------------------------------------------------------------

def _resolve_scaffold_root() -> Path:
    """Return the scaffold directory of the installed plugin.

    Exits with status 1 if the path cannot be found — the script must be
    invoked via /doc-migrate which sets CLAUDE_PLUGIN_ROOT automatically.
    """
    for env_var in ("CLAUDE_PLUGIN_ROOT", "IEC62304_PLUGIN_ROOT"):
        val = os.environ.get(env_var)
        if val:
            candidate = Path(val)
            if (candidate / "scaffold").is_dir():
                return candidate / "scaffold"
            # Maybe the env var already points to the scaffold dir directly
            if (candidate / "dt-config.yaml").is_file():
                return candidate

    default = Path.home() / ".claude" / "plugins" / "iec62304-writer"
    if (default / "scaffold").is_dir():
        return default / "scaffold"

    print(
        "ERROR: Plugin scaffold not found.\n"
        "  Set CLAUDE_PLUGIN_ROOT to the plugin root directory, or invoke\n"
        "  this script via the /doc-migrate command which sets it automatically.",
        file=sys.stderr,
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Section A — dt-config.yaml diff
# ---------------------------------------------------------------------------

SECTION_A_COMMENT = "# --- Added by /doc-migrate on {date} ---\n"


def _extract_top_level_blocks(text: str) -> dict[str, str]:
    """Return {key: raw_block_text} for each top-level key in a YAML text.

    Each block includes the comment lines immediately above the key and
    the key's own lines (including any nested content).  This is used for
    verbatim-append instead of parse-then-emit (which would destroy comments).
    """
    lines = text.splitlines(keepends=True)
    blocks: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []
    pending_comments: list[str] = []

    for line in lines:
        stripped = line.strip()
        # Collect comment / separator lines as "pending" — they belong to the
        # next top-level key if one follows immediately.
        if stripped.startswith("#") or stripped == "":
            if current_key is not None:
                current_lines.append(line)
            else:
                pending_comments.append(line)
            continue

        # Detect a top-level key (no leading spaces, `key:` pattern)
        import re
        m = re.match(r"^([A-Za-z_][\w\-]*)\s*:", line)
        if m and not line.startswith(" "):
            # Flush previous key
            if current_key is not None:
                blocks[current_key] = "".join(current_lines)
            current_key = m.group(1)
            current_lines = pending_comments + [line]
            pending_comments = []
        else:
            # Continuation line of the current key (indented)
            if current_key is not None:
                current_lines.append(line)
            else:
                pending_comments.append(line)

    # Flush last key
    if current_key is not None:
        blocks[current_key] = "".join(current_lines)

    return blocks


def audit_config(
    repo_root: Path,
    scaffold_root: Path,
) -> tuple[list[str], str, bool]:
    """Return (keys_to_add, append_block, user_file_missing).

    keys_to_add        — top-level keys missing from the user config
    append_block       — verbatim YAML text to append (empty string if nothing to add)
    user_file_missing  — True when dt-config.yaml does not exist in the target repo
                         (in that case, run `/doc-init` to scaffold the full file —
                         `--apply` is a poor substitute since it skips the scaffold
                         header and structure)
    """
    user_config_path = repo_root / "dt-config.yaml"
    scaffold_config_path = scaffold_root / "dt-config.yaml"

    if not scaffold_config_path.is_file():
        return [], "", False

    scaffold_text = scaffold_config_path.read_text(encoding="utf-8")
    scaffold_parsed = parse_yaml(scaffold_text)
    scaffold_keys = list(scaffold_parsed.keys())

    if not user_config_path.is_file():
        # Signal to the caller: scaffolding-needed, not a partial migration.
        return scaffold_keys, scaffold_text, True

    user_text = user_config_path.read_text(encoding="utf-8")
    user_parsed = parse_yaml(user_text)
    user_keys = set(user_parsed.keys())

    missing_keys = [k for k in scaffold_keys if k not in user_keys]
    if not missing_keys:
        return [], "", False

    # Build verbatim append block from scaffold source
    scaffold_blocks = _extract_top_level_blocks(scaffold_text)
    parts: list[str] = []
    for key in missing_keys:
        block = scaffold_blocks.get(key, f"{key}: null\n")
        parts.append(block)

    append_block = "".join(parts)
    return missing_keys, append_block, False


def apply_config(repo_root: Path, append_block: str, today: str) -> None:
    """Append missing keys to the user's dt-config.yaml."""
    user_config_path = repo_root / "dt-config.yaml"
    separator = f"\n{SECTION_A_COMMENT.format(date=today)}"
    current = user_config_path.read_text(encoding="utf-8")
    if not current.endswith("\n"):
        current += "\n"
    user_config_path.write_text(current + separator + append_block, encoding="utf-8")


# ---------------------------------------------------------------------------
# Section B — dt-clinical-context.md anchor diff
# ---------------------------------------------------------------------------

SECTION_B_COMMENT = "<!-- Added by /doc-migrate on {date} -->\n"
_ANCHOR_RE = __import__("re").compile(r"^##\s+([\w\-]+)\s*$", __import__("re").MULTILINE)


def _extract_anchors(text: str) -> list[str]:
    return _ANCHOR_RE.findall(text)


def _extract_anchor_blocks(text: str) -> dict[str, str]:
    """Return {anchor: full_section_text_including_header} for each ## anchor."""
    chunks = _ANCHOR_RE.split(text)
    blocks: dict[str, str] = {}
    for i in range(1, len(chunks), 2):
        anchor = chunks[i].strip()
        body = chunks[i + 1] if i + 1 < len(chunks) else ""
        blocks[anchor] = f"## {anchor}\n{body}"
    return blocks


def audit_clinical_context(
    repo_root: Path,
    scaffold_root: Path,
) -> tuple[list[str], str, bool]:
    """Return (anchors_to_add, append_block, user_file_missing)."""
    user_path = repo_root / "docs" / "dt-clinical-context.md"
    scaffold_path = scaffold_root / "docs" / "dt-clinical-context.md"

    if not scaffold_path.is_file():
        return [], "", False

    scaffold_text = scaffold_path.read_text(encoding="utf-8")
    scaffold_anchors = _extract_anchors(scaffold_text)

    if not user_path.is_file():
        return scaffold_anchors, scaffold_text, True

    user_text = user_path.read_text(encoding="utf-8")
    user_anchors = set(_extract_anchors(user_text))

    missing_anchors = [a for a in scaffold_anchors if a not in user_anchors]
    if not missing_anchors:
        return [], "", False

    scaffold_blocks = _extract_anchor_blocks(scaffold_text)
    parts: list[str] = []
    for anchor in missing_anchors:
        block = scaffold_blocks.get(anchor, f"## {anchor}\n\n[TODO]\n")
        parts.append(block)

    append_block = "\n".join(parts)
    return missing_anchors, append_block, False


def apply_clinical_context(repo_root: Path, append_block: str, today: str) -> None:
    """Append missing sections to the user's dt-clinical-context.md."""
    user_path = repo_root / "docs" / "dt-clinical-context.md"
    separator = f"\n{SECTION_B_COMMENT.format(date=today)}\n"
    current = user_path.read_text(encoding="utf-8")
    if not current.endswith("\n"):
        current += "\n"
    user_path.write_text(current + separator + append_block, encoding="utf-8")


# ---------------------------------------------------------------------------
# Section C — Items frontmatter completeness (read-only)
# ---------------------------------------------------------------------------

CATEGORIES = ("MAP", "SRS", "SDS", "TC", "RSK", "PRSK", "THR", "USC", "URSK")


def audit_items(repo_root: Path, scaffold_root: Path) -> dict[str, list[tuple[str, list[str]]]]:
    """Return {category: [(item_id, [missing_fields])]} for items with gaps.

    Never modifies any file.
    """
    result: dict[str, list[tuple[str, list[str]]]] = {}
    templates_dir = scaffold_root / "docs" / "templates"
    items_dir = repo_root / "docs" / "items"

    for cat in CATEGORIES:
        tpl_path = templates_dir / f"{cat.lower()}-item.template.md"
        if not tpl_path.is_file():
            continue

        tpl_text = tpl_path.read_text(encoding="utf-8")
        tpl_match = FRONTMATTER_RE.match(tpl_text)
        if not tpl_match:
            continue
        tpl_parsed = parse_yaml(tpl_match.group(1))

        # Filter out fields whose template default is an empty container or null.
        # These are typically rendered as Markdown body sections in real items
        # (e.g. TC `preconditions`/`steps`/`expected` are `[]` in the template
        # but filled in `## Preconditions` / `## Steps` etc.), so flagging them
        # as "missing" produces noisy false positives on existing items.
        def _is_required(value: object) -> bool:
            if value is None:
                return False
            if isinstance(value, (list, dict)) and not value:
                return False
            return True

        tpl_fields = {k for k, v in tpl_parsed.items() if _is_required(v)}

        cat_dir = items_dir / cat
        if not cat_dir.is_dir():
            continue

        incomplete: list[tuple[str, list[str]]] = []
        for item_path in sorted(cat_dir.glob("*.md")):
            item_text = item_path.read_text(encoding="utf-8")
            item_match = FRONTMATTER_RE.match(item_text)
            if not item_match:
                continue
            item_fields = set(parse_yaml(item_match.group(1)).keys())
            missing = sorted(tpl_fields - item_fields)
            if missing:
                item_id = item_path.stem
                incomplete.append((item_id, missing))

        if incomplete:
            result[cat] = incomplete

    return result


# ---------------------------------------------------------------------------
# Section D — tools/build_*.py audit
# ---------------------------------------------------------------------------

def audit_scripts(repo_root: Path, scaffold_root: Path) -> list[tuple[str, str]]:
    """Return [(script_name, status)] where status is MISSING or OUTDATED.

    Audits every `tools/*.py` file present in the scaffold — that includes
    `_lib.py` (shared helpers) on top of all `build_*.py` scripts. Without
    `_lib.py`, none of the build_*_export.py scripts can be imported.
    """
    scaffold_tools = scaffold_root / "tools"
    repo_tools = repo_root / "tools"
    issues: list[tuple[str, str]] = []

    candidates = sorted(
        list(scaffold_tools.glob("build_*.py")) + list(scaffold_tools.glob("_lib.py"))
    )
    for scaffold_script in candidates:
        name = scaffold_script.name
        repo_script = repo_tools / name
        if not repo_script.is_file():
            issues.append((name, "MISSING"))
        elif repo_script.stat().st_size != scaffold_script.stat().st_size:
            issues.append((name, "OUTDATED"))

    return issues


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

def render_report(
    today: str,
    config_keys: list[str],
    config_missing_file: bool,
    clinical_anchors: list[str],
    clinical_missing_file: bool,
    items_audit: dict[str, list[tuple[str, list[str]]]],
    scripts_audit: list[tuple[str, str]],
    apply_mode: bool,
) -> str:
    mode_label = "apply" if apply_mode else "dry-run"
    lines: list[str] = [
        f"# Migration report — {today} ({mode_label})",
        "",
    ]

    # TL;DR — high-level counters
    n_items_incomplete = sum(len(v) for v in items_audit.values())
    n_scripts_missing = sum(1 for _, s in scripts_audit if s == "MISSING")
    n_scripts_outdated = sum(1 for _, s in scripts_audit if s == "OUTDATED")
    lines += [
        "## TL;DR",
        "",
        f"- **A.** dt-config.yaml: "
        + ("file missing — run `/doc-init` first" if config_missing_file
           else (f"{len(config_keys)} key(s) to add" if config_keys else "✓ up to date")),
        f"- **B.** dt-clinical-context.md: "
        + ("file missing — run `/doc-init` first" if clinical_missing_file
           else (f"{len(clinical_anchors)} anchor(s) to add" if clinical_anchors else "✓ up to date")),
        f"- **C.** items with incomplete frontmatter: **{n_items_incomplete}** "
        f"across {len(items_audit)} categor{'ies' if len(items_audit) != 1 else 'y'}",
        f"- **D.** tools scripts: **{n_scripts_missing}** missing, "
        f"**{n_scripts_outdated}** outdated",
        "",
        "---",
        "",
    ]

    # A
    lines.append("## A. dt-config.yaml")
    lines.append("")
    if config_missing_file:
        lines += [
            "⚠ **`dt-config.yaml` does not exist in this repo.** This is not a",
            "migration scenario — the file has never been scaffolded.",
            "",
            "**Run `/doc-init` instead.** That will create the full file with",
            "the proper header comments, sections, and defaults. `--apply` is",
            "not appropriate here (it would create a malformed file without",
            "the scaffold structure).",
        ]
    elif not config_keys:
        lines.append("✓ Up to date")
    else:
        for k in config_keys:
            status = "ADDED" if apply_mode else "ADD"
            lines.append(f"- {k}: {status}")
    lines.append("")

    # B
    lines.append("## B. docs/dt-clinical-context.md")
    lines.append("")
    if clinical_missing_file:
        lines += [
            "⚠ **`docs/dt-clinical-context.md` does not exist in this repo.**",
            "Run `/doc-init` to scaffold the full file with all anchors.",
        ]
    elif not clinical_anchors:
        lines.append("✓ Up to date")
    else:
        for a in clinical_anchors:
            status = "ADDED" if apply_mode else "ADD"
            lines.append(f"- {a}: {status}")
    lines.append("")

    # C — group by missing-fields signature to compress repetition
    lines.append("## C. Items — frontmatter completeness")
    lines.append("")
    if not items_audit:
        lines.append("✓ All items match the current template")
    else:
        for cat, incomplete in sorted(items_audit.items()):
            lines.append(f"### {cat}")
            lines.append("")
            # Group items by their missing-fields signature
            groups: dict[tuple[str, ...], list[str]] = {}
            for item_id, missing in incomplete:
                groups.setdefault(tuple(missing), []).append(item_id)
            for missing_sig, item_ids in sorted(groups.items()):
                fields_str = ", ".join(missing_sig)
                if len(item_ids) == 1:
                    lines.append(f"- `{item_ids[0]}`: missing [{fields_str}]")
                else:
                    lines.append(
                        f"- **{len(item_ids)} items** all missing "
                        f"[{fields_str}]:"
                    )
                    # Show first 5, then "... +N more" if longer
                    preview = item_ids[:5]
                    rest = len(item_ids) - len(preview)
                    inline = ", ".join(f"`{i}`" for i in preview)
                    if rest > 0:
                        inline += f", ... (+{rest} more)"
                    lines.append(f"  {inline}")
            lines.append("")
    if items_audit:
        lines.append(
            "> Section C is read-only. Edit items manually or use"
            " `@risk-analyst refresh <ID>` to update individual items."
        )
    lines.append("")

    # D
    lines.append("## D. tools/build_*.py")
    lines.append("")
    if not scripts_audit:
        lines.append("✓ All scripts present and matching scaffold")
    else:
        for name, status in scripts_audit:
            if status == "MISSING":
                lines.append(
                    f"- {name}: MISSING — run `/doc-init --update` to install"
                )
            else:
                lines.append(
                    f"- {name}: OUTDATED — run `/doc-init --update` to refresh"
                )
    lines.append("")

    # Next actions
    lines.append("## Next actions")
    lines.append("")
    next_actions: list[str] = []

    # Always recommend /doc-init first when sentinel files are absent.
    if config_missing_file or clinical_missing_file:
        next_actions.append(
            "**Run `/doc-init` first** — sentinel files (dt-config.yaml or "
            "dt-clinical-context.md) are missing. `/doc-migrate --apply` is "
            "designed for partial updates, not initial scaffolding."
        )
    else:
        if config_keys and not apply_mode:
            next_actions.append(
                "Run `/doc-migrate --apply` to append missing keys to `dt-config.yaml`"
            )
        if clinical_anchors and not apply_mode:
            next_actions.append(
                "Run `/doc-migrate --apply` to append missing sections"
                " to `docs/dt-clinical-context.md`"
            )
    if items_audit:
        next_actions.append(
            "Review items listed in section C and add missing frontmatter fields manually"
        )
    if scripts_audit:
        next_actions.append(
            "Run `/doc-init --update` to refresh outdated or missing `tools/` scripts"
            " (build_*.py and _lib.py)"
        )
    if not next_actions:
        next_actions.append("No action required — project is in sync with the current plugin version")

    for action in next_actions:
        lines.append(f"- {action}")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit migration state between target repo and current plugin scaffold. "
            "Dry-run by default; use --apply to perform additive updates."
        )
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply additive changes to dt-config.yaml and dt-clinical-context.md",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print report to stdout instead of docs/generated/migration-report.md",
    )
    args = parser.parse_args(argv)

    repo_root = Path.cwd()
    scaffold_root = _resolve_scaffold_root()
    today = date.today().isoformat()

    # --- A ---
    config_keys, config_append, config_missing_file = audit_config(repo_root, scaffold_root)

    # --- B ---
    clinical_anchors, clinical_append, clinical_missing_file = audit_clinical_context(
        repo_root, scaffold_root
    )

    # --- C ---
    items_audit = audit_items(repo_root, scaffold_root)

    # --- D ---
    scripts_audit = audit_scripts(repo_root, scaffold_root)

    # --- Apply ---
    if args.apply:
        if config_missing_file:
            print(
                "[A] SKIP: dt-config.yaml does not exist. Run `/doc-init` to "
                "scaffold the full file with proper header/structure.",
                file=sys.stderr,
            )
        elif config_append:
            print(
                f"[A] Appending {len(config_keys)} key(s) to dt-config.yaml: "
                + ", ".join(config_keys)
            )
            apply_config(repo_root, config_append, today)
        if clinical_missing_file:
            print(
                "[B] SKIP: docs/dt-clinical-context.md does not exist. Run "
                "`/doc-init` to scaffold the full file.",
                file=sys.stderr,
            )
        elif clinical_append:
            print(
                f"[B] Appending {len(clinical_anchors)} section(s) to"
                " docs/dt-clinical-context.md: " + ", ".join(clinical_anchors)
            )
            apply_clinical_context(repo_root, clinical_append, today)

    # --- Report ---
    report = render_report(
        today=today,
        config_keys=config_keys,
        config_missing_file=config_missing_file,
        clinical_anchors=clinical_anchors,
        clinical_missing_file=clinical_missing_file,
        items_audit=items_audit,
        scripts_audit=scripts_audit,
        apply_mode=args.apply,
    )

    if args.stdout:
        print(report)
    else:
        out_dir = repo_root / "docs" / "generated"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "migration-report.md"
        out_path.write_text(report, encoding="utf-8")
        print(f"Report written to {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
