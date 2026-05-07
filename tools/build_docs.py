#!/usr/bin/env python3
"""
Build doc agrégés à partir de l'item-store local.

Lit `docs/items/<CAT>/*.md`, parse le frontmatter YAML, produit :
  - docs/generated/10_SRS.md
  - docs/generated/20_SDS.md
  - docs/generated/30_test_evidence.md
  - docs/generated/40_traceability.md
  - docs/generated/coverage.json

Ne dépend que de la stdlib (pas de PyYAML — parser inline simple suffit
pour le sous-ensemble YAML utilisé par les frontmatters).

Usage:
    python tools/build_docs.py [--strict]

`--strict` => exit ≠ 0 si tout [TODO] ou [GAP-62304] non résolu.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS_DIR = ROOT / "docs" / "items"
OUT_DIR = ROOT / "docs" / "generated"

CATEGORIES = ("SRS", "SDS", "TC", "RSK")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)


@dataclass
class Item:
    id: str
    category: str
    path: Path
    frontmatter: dict
    body: str

    @property
    def status(self) -> str:
        return self.frontmatter.get("status", "Draft")

    @property
    def title(self) -> str:
        return self.frontmatter.get("title", "(sans titre)")

    @property
    def links(self) -> dict:
        return self.frontmatter.get("links") or {}


def parse_yaml_frontmatter(text: str) -> dict:
    """Parser YAML minimaliste pour le sous-ensemble utilisé.

    Supporte: scalaires, listes inline `[a, b]`, listes en blocs `- x`,
    blocs imbriqués sur 2 niveaux, scalaires `|` (multi-ligne).
    """
    result: dict = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.strip().startswith("#"):
            i += 1
            continue
        indent = len(line) - len(line.lstrip(" "))
        if indent != 0:
            i += 1
            continue
        m = re.match(r"^([A-Za-z_][\w\-]*)\s*:\s*(.*)$", line)
        if not m:
            i += 1
            continue
        key, raw = m.group(1), m.group(2).strip()
        if raw == "" or raw == "|":
            # Bloc — soit liste de "- ...", soit dict imbriqué, soit "|" multi-ligne.
            block_lines: list[str] = []
            i += 1
            while i < len(lines):
                nxt = lines[i]
                if not nxt.strip() and len(block_lines) == 0:
                    i += 1
                    continue
                nxt_indent = len(nxt) - len(nxt.lstrip(" "))
                if nxt.strip() and nxt_indent == 0:
                    break
                block_lines.append(nxt)
                i += 1
            if raw == "|":
                # multi-ligne scalaire — dédent commun
                stripped = [bl[2:] if bl.startswith("  ") else bl for bl in block_lines]
                result[key] = "\n".join(stripped).rstrip("\n")
            elif block_lines and block_lines[0].lstrip(" ").startswith("- "):
                # liste
                items = []
                for bl in block_lines:
                    s = bl.strip()
                    if s.startswith("- "):
                        items.append(_coerce_scalar(s[2:].strip()))
                result[key] = items
            else:
                # dict imbriqué — un niveau
                sub: dict = {}
                for bl in block_lines:
                    if not bl.strip() or bl.strip().startswith("#"):
                        continue
                    sm = re.match(r"^\s+([A-Za-z_][\w\-]*)\s*:\s*(.*)$", bl)
                    if not sm:
                        continue
                    sk, sv = sm.group(1), sm.group(2).strip()
                    if sv == "":
                        sub[sk] = []
                    elif sv.startswith("[") and sv.endswith("]"):
                        sub[sk] = _parse_inline_list(sv)
                    else:
                        sub[sk] = _coerce_scalar(sv)
                # second pass : listes en bloc à l'intérieur du dict imbriqué
                cur_key = None
                for bl in block_lines:
                    if re.match(r"^\s+[A-Za-z_][\w\-]*\s*:\s*$", bl):
                        cur_key = bl.strip().rstrip(":")
                        sub.setdefault(cur_key, [])
                    elif cur_key and bl.strip().startswith("- "):
                        sub[cur_key].append(_coerce_scalar(bl.strip()[2:].strip()))
                    elif bl.strip() and not re.match(r"^\s+[A-Za-z_][\w\-]*\s*:", bl):
                        cur_key = None
                result[key] = sub
        elif raw.startswith("[") and raw.endswith("]"):
            result[key] = _parse_inline_list(raw)
            i += 1
        else:
            result[key] = _coerce_scalar(raw)
            i += 1
    return result


def _parse_inline_list(s: str) -> list:
    inner = s.strip()[1:-1].strip()
    if not inner:
        return []
    parts = [p.strip() for p in inner.split(",")]
    return [_coerce_scalar(p) for p in parts]


def _coerce_scalar(s: str):
    s = s.strip()
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    if s.startswith("'") and s.endswith("'"):
        return s[1:-1]
    if s in ("true", "True"):
        return True
    if s in ("false", "False"):
        return False
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if re.fullmatch(r"-?\d+\.\d+", s):
        return float(s)
    return s


def load_items() -> dict[str, list[Item]]:
    out: dict[str, list[Item]] = {c: [] for c in CATEGORIES}
    if not ITEMS_DIR.exists():
        return out
    for cat in CATEGORIES:
        cat_dir = ITEMS_DIR / cat
        if not cat_dir.is_dir():
            continue
        for path in sorted(cat_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            m = FRONTMATTER_RE.match(text)
            if not m:
                print(f"WARN: pas de frontmatter dans {path}", file=sys.stderr)
                continue
            fm = parse_yaml_frontmatter(m.group(1))
            body = m.group(2)
            item_id = fm.get("id") or path.stem
            if item_id != path.stem:
                print(
                    f"WARN: id {item_id} != nom de fichier {path.name}",
                    file=sys.stderr,
                )
            out[cat].append(
                Item(id=item_id, category=cat, path=path, frontmatter=fm, body=body)
            )
    return out


def render_aggregate(title: str, items: list[Item], category: str) -> str:
    lines = [f"# {title}", "", f"_Généré le {date.today().isoformat()}_", ""]
    if not items:
        lines += ["_(aucun item)_", ""]
        return "\n".join(lines)
    for it in items:
        if it.status == "Deprecated":
            continue
        lines.append(f"## {it.id} — {it.title}")
        lines.append("")
        lines.append(f"**Statut :** {it.status} · **Version :** "
                     f"{it.frontmatter.get('version', '?')}")
        if category == "SRS":
            lines.append(
                f"**Vérification :** {it.frontmatter.get('verification', '?')} · "
                f"**Priorité :** {it.frontmatter.get('priority', '?')}"
            )
        if category == "SDS":
            lines.append(f"**Module :** `{it.frontmatter.get('module', '?')}`")
            impls = it.links.get("implements") or []
            if impls:
                lines.append(f"**Implémente :** {', '.join(impls)}")
        if category == "TC":
            verif = it.links.get("verifies") or []
            lines.append(
                f"**Type :** {it.frontmatter.get('type', '?')} · "
                f"**Auto :** {it.frontmatter.get('automated', '?')}"
            )
            if verif:
                lines.append(f"**Vérifie :** {', '.join(verif)}")
        srcs = it.frontmatter.get("source") or []
        if srcs:
            lines.append("**Source :** " + ", ".join(f"`{s}`" for s in srcs))
        lines.append("")
        lines.append(it.body.strip())
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def build_traceability(by_cat: dict[str, list[Item]]) -> tuple[str, dict]:
    srs = [i for i in by_cat["SRS"] if i.status != "Deprecated"]
    sds = [i for i in by_cat["SDS"] if i.status != "Deprecated"]
    tc = [i for i in by_cat["TC"] if i.status != "Deprecated"]

    impl_by_srs: dict[str, list[str]] = defaultdict(list)
    for s in sds:
        for srs_id in s.links.get("implements") or []:
            impl_by_srs[srs_id].append(s.id)

    verif_by_srs: dict[str, list[str]] = defaultdict(list)
    for t in tc:
        for srs_id in t.links.get("verifies") or []:
            verif_by_srs[srs_id].append(t.id)

    must = [s for s in srs if s.frontmatter.get("priority", "Must") == "Must"]
    impl_count = sum(1 for s in srs if impl_by_srs[s.id])
    verif_must_count = sum(1 for s in must if verif_by_srs[s.id])

    coverage = {
        "srs_count": len(srs),
        "sds_count": len(sds),
        "tc_count": len(tc),
        "implementation_rate": (impl_count / len(srs)) if srs else 0.0,
        "verification_rate_must": (verif_must_count / len(must)) if must else 0.0,
        "orphans": {
            "sds": [s.id for s in sds if not (s.links.get("implements") or [])],
            "tc": [t.id for t in tc if not (t.links.get("verifies") or [])],
            "srs_no_impl": [s.id for s in srs if not impl_by_srs[s.id]],
            "srs_no_verif_must": [s.id for s in must if not verif_by_srs[s.id]],
        },
    }

    lines = [
        "# Matrice de traçabilité",
        "",
        f"_Généré le {date.today().isoformat()}_",
        "",
        "## Synthèse",
        "",
        "| Métrique | Valeur |",
        "|---|---|",
        f"| Items SRS (actifs) | {coverage['srs_count']} |",
        f"| Items SDS (actifs) | {coverage['sds_count']} |",
        f"| Items TC (actifs) | {coverage['tc_count']} |",
        f"| Couverture implémentation | {impl_count}/{len(srs)} "
        f"({coverage['implementation_rate']:.0%}) |",
        f"| Couverture vérification (Must) | {verif_must_count}/{len(must)} "
        f"({coverage['verification_rate_must']:.0%}) |",
        "",
        "## SRS → SDS → TC",
        "",
        "| SRS | Titre | SDS | TC |",
        "|---|---|---|---|",
    ]
    for s in srs:
        sds_list = ", ".join(impl_by_srs[s.id]) or "—"
        tc_list = ", ".join(verif_by_srs[s.id]) or "—"
        lines.append(f"| {s.id} | {s.title} | {sds_list} | {tc_list} |")

    if coverage["orphans"]["sds"]:
        lines += ["", "## SDS sans exigence implémentée"]
        lines += [f"- {x}" for x in coverage["orphans"]["sds"]]
    if coverage["orphans"]["tc"]:
        lines += ["", "## TC sans exigence vérifiée"]
        lines += [f"- {x}" for x in coverage["orphans"]["tc"]]

    return "\n".join(lines) + "\n", coverage


def find_todo_markers() -> list[tuple[Path, int, str]]:
    hits: list[tuple[Path, int, str]] = []
    if not ITEMS_DIR.exists():
        return hits
    for path in ITEMS_DIR.rglob("*.md"):
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "[TODO]" in line or "[GAP-62304]" in line:
                hits.append((path, n, line.strip()))
    return hits


def main() -> int:
    strict = "--strict" in sys.argv[1:]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    by_cat = load_items()

    (OUT_DIR / "10_SRS.md").write_text(
        render_aggregate("Software Requirements Specification (SRS)",
                         by_cat["SRS"], "SRS"),
        encoding="utf-8",
    )
    (OUT_DIR / "20_SDS.md").write_text(
        render_aggregate("Software Design Specification (SDS)",
                         by_cat["SDS"], "SDS"),
        encoding="utf-8",
    )
    (OUT_DIR / "30_test_evidence.md").write_text(
        render_aggregate("Plan & preuves de vérification",
                         by_cat["TC"], "TC"),
        encoding="utf-8",
    )

    matrix_md, coverage = build_traceability(by_cat)
    (OUT_DIR / "40_traceability.md").write_text(matrix_md, encoding="utf-8")
    (OUT_DIR / "coverage.json").write_text(
        json.dumps(coverage, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(f"OK — items SRS={len(by_cat['SRS'])} SDS={len(by_cat['SDS'])} "
          f"TC={len(by_cat['TC'])}")
    print(f"  impl={coverage['implementation_rate']:.0%} "
          f"verif_must={coverage['verification_rate_must']:.0%}")
    print(f"  → {OUT_DIR}")

    if strict:
        todos = find_todo_markers()
        if todos:
            print(f"STRICT — {len(todos)} marqueur(s) [TODO]/[GAP-62304] :",
                  file=sys.stderr)
            for path, n, line in todos:
                rel = path.relative_to(ROOT)
                print(f"  {rel}:{n}: {line}", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
