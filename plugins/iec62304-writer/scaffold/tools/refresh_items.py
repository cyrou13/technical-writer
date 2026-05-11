#!/usr/bin/env python3
"""Refresh item frontmatters with fields that exist in the current template
but are missing from existing items. Conservative additive-only mode.

Use case: after a plugin upgrade that extends an item's frontmatter schema
(e.g. v0.5 added ISO 14971 §C.2 fields to RSK, v0.6 added CIA triad to THR),
existing items written before the upgrade lack those fields. This script
adds them as `[TODO ...]` placeholders without touching the existing
content or the Markdown body.

Reads:
    docs/items/<CAT>/*.md           (target items)
    docs/templates/<cat>-item.template.md   (per-category target schema)

Writes (only with --apply):
    docs/items/<CAT>/*.md           (in-place additive update)

Behaviour:
- Missing scalar field → inserted with value `"[TODO <field>]"` (string).
- Missing block-scalar / list field → inserted with default `[]` or
  `"[TODO]"` depending on the template's hint.
- Missing nested dict → inserted with the template's default structure.
- Existing fields are NEVER overwritten.
- Body Markdown is NEVER touched.
- On modification: bump `version` patch (last segment +1) and reset
  `status: Approved → Draft`.

CLI:
    python tools/refresh_items.py [--apply] [--cat CAT] [--stdout]

Modes:
- Default (no --apply): dry-run, lists every item that would be modified
  and the fields that would be added. Reports to docs/generated/refresh-report.md.
- --apply: writes the updates in-place. Always preserves existing content.
- --cat CAT: limit to one category (e.g. RSK, THR). Defaults to all.

Stdlib only. Python 3.12+.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import FRONTMATTER_RE, parse_yaml  # noqa: E402

ROOT = Path.cwd()
ITEMS_DIR = ROOT / "docs" / "items"
REPORT_PATH = ROOT / "docs" / "generated" / "refresh-report.md"


def _resolve_templates_dir() -> Path:
    """Resolve the templates dir. Plugin scaffold has priority over local copy
    (the local copy may be stale relative to the current plugin version)."""
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if plugin_root:
        scaffold = Path(plugin_root) / "scaffold" / "docs" / "templates"
        if scaffold.is_dir():
            return scaffold
    # Fallback: also try the script's own location (when this script lives
    # inside the plugin scaffold itself rather than copied into a target repo)
    here = Path(__file__).resolve().parent.parent / "docs" / "templates"
    if here.is_dir():
        return here
    return ROOT / "docs" / "templates"


TEMPLATES_DIR = _resolve_templates_dir()

CATEGORIES = ("MAP", "SRS", "SDS", "TC", "RSK", "PRSK", "THR", "USC", "URSK")


# ---------------------------------------------------------------------------
# Template parsing — preserve the raw line(s) per top-level key so we can
# re-emit them verbatim into existing items.
# ---------------------------------------------------------------------------


def _extract_template_blocks(text: str) -> dict[str, list[str]]:
    """Return {key: list of raw lines that define this key} from a YAML
    frontmatter text. Lines include the key line itself plus any indented
    continuation lines.
    """
    blocks: dict[str, list[str]] = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^([A-Za-z_][\w\-]*)\s*:", line)
        if m and not line.startswith(" "):
            key = m.group(1)
            block = [line]
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if nxt.strip() == "":
                    # blank line ends the block
                    break
                # indented continuation
                if nxt.startswith(" ") or nxt.startswith("\t"):
                    block.append(nxt)
                    i += 1
                    continue
                # block scalar continuation (e.g. after "|") — lines with content
                # at column 0 belong to the next key, stop.
                break
            blocks[key] = block
        else:
            i += 1
    return blocks


def _template_fields(cat: str) -> tuple[dict[str, list[str]], list[str]]:
    """Return (raw_blocks_by_key, ordered_keys) from the template frontmatter.

    Filters out fields whose default value is None / empty container — those
    are considered optional (typically rendered as Markdown body sections).
    """
    tpl_path = TEMPLATES_DIR / f"{cat.lower()}-item.template.md"
    if not tpl_path.is_file():
        return {}, []
    text = tpl_path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}, []
    fm_text = m.group(1)
    parsed = parse_yaml(fm_text)
    raw_blocks = _extract_template_blocks(fm_text)

    def _is_required(value: object) -> bool:
        if value is None:
            return False
        if isinstance(value, (list, dict)) and not value:
            return False
        return True

    ordered_keys = [k for k in parsed.keys() if _is_required(parsed[k])]
    return raw_blocks, ordered_keys


# ---------------------------------------------------------------------------
# Item refresh
# ---------------------------------------------------------------------------


def _bump_version(version: str) -> str:
    """Bump the patch segment of a semver string. Fallback: append .1."""
    parts = version.strip().split(".")
    if len(parts) == 3 and all(p.isdigit() for p in parts):
        major, minor, patch = parts
        return f"{major}.{minor}.{int(patch) + 1}"
    return f"{version}.1"


def _insert_fields_in_frontmatter(
    fm_text: str,
    fields_to_add: list[str],
    template_blocks: dict[str, list[str]],
) -> str:
    """Append the missing field blocks to the existing frontmatter text.

    Strategy: append before the closing `---` (or at the end of fm_text).
    Each new field is rendered from the template's raw block, with scalar
    values replaced by `"[TODO <field>]"` placeholders to make it obvious
    they need attention.
    """
    inserts: list[str] = []
    for field_name in fields_to_add:
        block = template_blocks.get(field_name)
        if not block:
            inserts.append(f'{field_name}: "[TODO {field_name}]"')
            continue
        # First line: replace the value after the colon with a [TODO] placeholder
        # if it was a scalar. Keep nested blocks (block scalars, lists, dicts)
        # as-is from the template — they already use [TODO ...] internally.
        first = block[0]
        m = re.match(r"^([A-Za-z_][\w\-]*\s*:\s*)(.*)$", first)
        if m and len(block) == 1:
            key_part, value_part = m.group(1), m.group(2).strip()
            # If the value is a simple scalar (not `|`, not `[]`, not empty),
            # replace it with a placeholder for clarity.
            if value_part and value_part not in ("|", "[]", "{}", "null"):
                # Keep the scalar as the template suggests (it's an enum default
                # like `Negligible` — useful starting point).
                inserts.append(first)
            elif not value_part:
                inserts.append(f'{key_part}"[TODO {field_name}]"')
            else:
                inserts.append(first)
        else:
            inserts.extend(block)

    if not inserts:
        return fm_text

    # Update `updated:` to today and bump `version` if present.
    today = date.today().isoformat()
    updated_lines = []
    bumped = False
    status_reset = False
    for line in fm_text.splitlines():
        if re.match(r"^updated\s*:", line):
            updated_lines.append(f"updated: {today}")
            continue
        m_v = re.match(r"^version\s*:\s*(.+)$", line)
        if m_v and not bumped:
            updated_lines.append(f"version: {_bump_version(m_v.group(1).strip())}")
            bumped = True
            continue
        m_s = re.match(r"^status\s*:\s*Approved\s*$", line)
        if m_s and not status_reset:
            updated_lines.append("status: Draft")
            status_reset = True
            continue
        updated_lines.append(line)

    return "\n".join(updated_lines) + "\n" + "\n".join(inserts)


def refresh_item(
    item_path: Path,
    template_blocks: dict[str, list[str]],
    template_keys: list[str],
    apply_mode: bool,
) -> tuple[bool, list[str]]:
    """Return (would_change, missing_fields).

    If `apply_mode`, also writes the updated file in-place.
    """
    text = item_path.read_text(encoding="utf-8")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return False, []

    fm_text, body = m.group(1), m.group(2)
    fm_parsed = parse_yaml(fm_text)
    existing_keys = set(fm_parsed.keys())

    missing = [k for k in template_keys if k not in existing_keys]
    if not missing:
        return False, []

    if apply_mode:
        new_fm = _insert_fields_in_frontmatter(fm_text, missing, template_blocks)
        new_text = f"---\n{new_fm}\n---\n{body}"
        item_path.write_text(new_text, encoding="utf-8")

    return True, missing


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def run(cat_filter: str | None, apply_mode: bool, stdout: bool) -> int:
    if not ITEMS_DIR.is_dir():
        print(f"ERROR: {ITEMS_DIR} does not exist.", file=sys.stderr)
        return 1

    cats = [cat_filter] if cat_filter else list(CATEGORIES)
    lines = [f"# Refresh report — {date.today().isoformat()} "
             f"({'apply' if apply_mode else 'dry-run'})", ""]
    total_changed = 0
    total_fields = 0

    for cat in cats:
        cat_dir = ITEMS_DIR / cat
        if not cat_dir.is_dir():
            continue
        template_blocks, template_keys = _template_fields(cat)
        if not template_keys:
            continue

        changed_items: list[tuple[str, list[str]]] = []
        for item_path in sorted(cat_dir.glob("*.md")):
            would_change, missing = refresh_item(
                item_path, template_blocks, template_keys, apply_mode
            )
            if would_change:
                changed_items.append((item_path.stem, missing))
                total_changed += 1
                total_fields += len(missing)

        if changed_items:
            lines.append(f"## {cat}")
            lines.append("")
            # Group by missing-fields signature
            groups: dict[tuple[str, ...], list[str]] = {}
            for item_id, missing in changed_items:
                groups.setdefault(tuple(missing), []).append(item_id)
            for sig, ids in sorted(groups.items()):
                action = "Updated" if apply_mode else "Would update"
                lines.append(f"- {action} **{len(ids)} items** with fields "
                             f"[{', '.join(sig)}]:")
                preview = ids[:5]
                rest = len(ids) - len(preview)
                inline = ", ".join(f"`{i}`" for i in preview)
                if rest > 0:
                    inline += f", ... (+{rest} more)"
                lines.append(f"  {inline}")
            lines.append("")

    lines += [
        "## Summary",
        "",
        f"- Items {'modified' if apply_mode else 'that would be modified'}: "
        f"**{total_changed}**",
        f"- Total fields {'added' if apply_mode else 'to add'}: **{total_fields}**",
        "",
    ]
    if not apply_mode:
        lines.append(
            "Run `python tools/refresh_items.py --apply` to apply the changes. "
            "Each new field is inserted as a `[TODO <field>]` placeholder — "
            "review and fill in manually before signing the item."
        )
    else:
        lines.append(
            "Each added field is a `[TODO <field>]` placeholder. The `version` "
            "has been bumped (patch) and any `status: Approved` reset to "
            "`Draft`. Review each modified item before re-approving."
        )

    report = "\n".join(lines) + "\n"
    if stdout:
        print(report)
    else:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(report, encoding="utf-8")
        print(str(REPORT_PATH))

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Refresh item frontmatters with missing fields from the current "
            "template. Adds [TODO] placeholders; never overwrites existing "
            "content or the Markdown body."
        )
    )
    parser.add_argument("--apply", action="store_true",
                        help="Apply changes in-place. Default is dry-run.")
    parser.add_argument("--cat", type=str, default=None,
                        help="Limit to one category (RSK, THR, ...).")
    parser.add_argument("--stdout", action="store_true",
                        help="Print report to stdout instead of docs/generated/refresh-report.md.")
    args = parser.parse_args()
    return run(args.cat, args.apply, args.stdout)


if __name__ == "__main__":
    sys.exit(main())
