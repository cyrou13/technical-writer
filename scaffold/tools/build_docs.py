#!/usr/bin/env python3
"""
Build doc agrégés à partir de l'item-store local.

Lit `docs/items/<CAT>/*.md`, parse le frontmatter YAML, produit :
  - docs/generated/10_SRS.md
  - docs/generated/20_SDS.md
  - docs/generated/30_STD.md                 (Software Test Description, IEEE 829)
  - docs/generated/40_traceability.md
  - docs/generated/50_risk_analysis.md       (safety - ISO 14971 / 62304 §7)
  - docs/generated/60_cyber_risk_analysis.md (cyber - IEC 81001-5-1 / STRIDE)
  - docs/generated/_to_implement.md
  - docs/generated/coverage.json

Ne dépend que de la stdlib.

Usage:
    python tools/build_docs.py [--strict]

`--strict` => exit ≠ 0 si :
  - tout marqueur [TODO], [GAP-62304] ou [GAP-CYBER] dans les items,
  - tout RSK avec `severity: Critical|Catastrophic`,
  - tout RSK ou THR avec `residual_acceptable: false`,
  - tout RSK ou THR avec `acceptable: false` sans aucun contrôle.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ITEMS_DIR = ROOT / "docs" / "items"
OUT_DIR = ROOT / "docs" / "generated"

CATEGORIES = ("SRS", "SDS", "TC", "RSK", "THR")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)

CLASS_A_INVALIDATING_SEVERITY = {"Critical", "Catastrophic"}


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

    @property
    def mitigates(self) -> list[str]:
        return list(self.links.get("mitigates") or [])


# ---------------------------------------------------------------------------
# YAML mini-parser (sous-ensemble utilisé par les frontmatters)
# ---------------------------------------------------------------------------


def parse_yaml_frontmatter(text: str) -> dict:
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
                stripped = [bl[2:] if bl.startswith("  ") else bl for bl in block_lines]
                result[key] = "\n".join(stripped).rstrip("\n")
            elif block_lines and block_lines[0].lstrip(" ").startswith("- "):
                items = []
                for bl in block_lines:
                    s = bl.strip()
                    if s.startswith("- "):
                        items.append(_coerce_scalar(s[2:].strip()))
                result[key] = items
            else:
                sub: dict = {}
                cur_key = None
                for bl in block_lines:
                    if not bl.strip() or bl.strip().startswith("#"):
                        continue
                    sm = re.match(r"^\s+([A-Za-z_][\w\-]*)\s*:\s*(.*)$", bl)
                    if sm:
                        sk, sv = sm.group(1), sm.group(2).strip()
                        if sv == "":
                            sub[sk] = []
                            cur_key = sk
                        elif sv.startswith("[") and sv.endswith("]"):
                            sub[sk] = _parse_inline_list(sv)
                            cur_key = None
                        else:
                            sub[sk] = _coerce_scalar(sv)
                            cur_key = None
                    elif cur_key and bl.strip().startswith("- "):
                        sub[cur_key].append(_coerce_scalar(bl.strip()[2:].strip()))
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


# ---------------------------------------------------------------------------
# Chargement
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Calculs de liens / couvertures
# ---------------------------------------------------------------------------


def reverse_index(items: dict[str, list[Item]]):
    """Calcule les index inverses :
    - impl_by_srs[srs_id]      = IDs SDS qui implémentent
    - verif_by_srs[srs_id]     = IDs TC qui vérifient
    - controls_by_target[id]   = Items (SRS/SDS/TC) qui mitigent ce RSK ou THR
    """
    impl_by_srs: dict[str, list[str]] = defaultdict(list)
    for s in items["SDS"]:
        if s.status == "Deprecated":
            continue
        for srs_id in s.links.get("implements") or []:
            impl_by_srs[srs_id].append(s.id)

    verif_by_srs: dict[str, list[str]] = defaultdict(list)
    for t in items["TC"]:
        if t.status == "Deprecated":
            continue
        for srs_id in t.links.get("verifies") or []:
            verif_by_srs[srs_id].append(t.id)

    controls_by_target: dict[str, list[Item]] = defaultdict(list)
    for cat in ("SRS", "SDS", "TC"):
        for it in items[cat]:
            if it.status == "Deprecated":
                continue
            for tgt_id in it.mitigates:
                controls_by_target[tgt_id].append(it)

    return impl_by_srs, verif_by_srs, controls_by_target


# ---------------------------------------------------------------------------
# Rendu
# ---------------------------------------------------------------------------


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
        lines.append(
            f"**Statut :** {it.status} · **Version :** "
            f"{it.frontmatter.get('version', '?')}"
        )
        if category == "SRS":
            lines.append(
                f"**Vérification :** {it.frontmatter.get('verification', '?')} · "
                f"**Priorité :** {it.frontmatter.get('priority', '?')}"
            )
            mit = it.mitigates
            if mit:
                lines.append(f"**Mitigation de :** {', '.join(mit)}")
        if category == "SDS":
            lines.append(f"**Module :** `{it.frontmatter.get('module', '?')}`")
            impls = it.links.get("implements") or []
            if impls:
                lines.append(f"**Implémente :** {', '.join(impls)}")
            mit = it.mitigates
            if mit:
                lines.append(f"**Mitige :** {', '.join(mit)}")
        if category == "TC":
            verif = it.links.get("verifies") or []
            lines.append(
                f"**Type :** {it.frontmatter.get('type', '?')} · "
                f"**Auto :** {it.frontmatter.get('automated', '?')}"
            )
            if verif:
                lines.append(f"**Vérifie :** {', '.join(verif)}")
            mit = it.mitigates
            if mit:
                lines.append(f"**Mitige :** {', '.join(mit)}")
        srcs = it.frontmatter.get("source") or []
        if srcs:
            lines.append("**Source :** " + ", ".join(f"`{s}`" for s in srcs))
        lines.append("")
        lines.append(it.body.strip())
        lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def build_traceability(by_cat, impl_by_srs, verif_by_srs):
    srs = [i for i in by_cat["SRS"] if i.status != "Deprecated"]
    sds = [i for i in by_cat["SDS"] if i.status != "Deprecated"]
    tc = [i for i in by_cat["TC"] if i.status != "Deprecated"]

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


def build_risk_analysis(by_cat, controls_by_target, impl_by_srs, verif_by_srs):
    """Renvoie (markdown, dict d'analyse pour coverage et to_implement)."""
    rsks = [r for r in by_cat["RSK"] if r.status != "Deprecated"]

    lines = [
        "# Analyse de risques (IEC 62304 §7 — Classe A)",
        "",
        f"_Généré le {date.today().isoformat()}_",
        "",
    ]

    if not rsks:
        lines += ["_(aucun risque enregistré)_", ""]
        return "\n".join(lines), {
            "rsk_count": 0,
            "rsk_unmitigated": [],
            "rsk_residual_unacceptable": [],
            "rsk_class_a_invalidating": [],
            "rsk_summary": [],
        }

    summary: list[dict] = []
    unmitigated: list[str] = []
    residual_unacceptable: list[str] = []
    class_a_invalidating: list[str] = []

    lines += [
        "## Synthèse",
        "",
        "| RSK | Titre | Sévérité | Niveau | Initial OK | Résiduel OK | # Contrôles |",
        "|---|---|---|---|---|---|---|",
    ]

    for rsk in rsks:
        fm = rsk.frontmatter
        sev = fm.get("severity", "Negligible")
        prob = fm.get("probability", "Remote")
        level = fm.get("risk_level", "Low")
        init_ok = bool(fm.get("acceptable", True))
        res_ok = bool(fm.get("residual_acceptable", True))
        controls = controls_by_target.get(rsk.id, [])

        if sev in CLASS_A_INVALIDATING_SEVERITY:
            class_a_invalidating.append(rsk.id)
        if not init_ok and not controls:
            unmitigated.append(rsk.id)
        if not res_ok:
            residual_unacceptable.append(rsk.id)

        summary.append(
            {
                "id": rsk.id,
                "title": rsk.title,
                "severity": sev,
                "probability": prob,
                "level": level,
                "acceptable_initial": init_ok,
                "residual_acceptable": res_ok,
                "controls": [c.id for c in controls],
            }
        )

        lines.append(
            f"| {rsk.id} | {rsk.title} | {sev} | {level} | "
            f"{'✓' if init_ok else '✗'} | {'✓' if res_ok else '✗'} | "
            f"{len(controls)} |"
        )

    lines += ["", "## Détail par RSK", ""]

    for rsk in rsks:
        fm = rsk.frontmatter
        lines.append(f"### {rsk.id} — {rsk.title}")
        lines.append("")
        lines.append(
            f"**Statut :** {rsk.status} · **Version :** {fm.get('version', '?')}"
        )
        lines.append(
            f"**Sévérité :** {fm.get('severity', '?')} · "
            f"**Probabilité :** {fm.get('probability', '?')} · "
            f"**Niveau :** {fm.get('risk_level', '?')}"
        )
        lines.append(
            f"**Acceptable (initial) :** "
            f"{'oui' if fm.get('acceptable', True) else 'non'} · "
            f"**Résiduel acceptable :** "
            f"{'oui' if fm.get('residual_acceptable', True) else 'non'}"
        )
        srcs = fm.get("source") or []
        if srcs:
            lines.append("**Source :** " + ", ".join(f"`{s}`" for s in srcs))
        lines.append("")

        controls = controls_by_target.get(rsk.id, [])
        if controls:
            lines.append("**Contrôles :**")
            lines.append("")
            lines.append("| Item | Catégorie | Implémenté | Vérifié |")
            lines.append("|---|---|---|---|")
            for c in controls:
                if c.category == "SRS":
                    impl = "✓" if impl_by_srs.get(c.id) else "✗"
                    verif = "✓" if verif_by_srs.get(c.id) else "✗"
                elif c.category == "SDS":
                    impl = "✓ (design)"
                    verif = "n/a"
                else:  # TC
                    impl = "n/a"
                    verif = "✓ (test)"
                lines.append(f"| {c.id} | {c.category} | {impl} | {verif} |")
            lines.append("")
        else:
            lines.append("_Aucun contrôle enregistré._")
            lines.append("")
        lines.append(rsk.body.strip())
        lines.append("")
        lines.append("---")
        lines.append("")

    if class_a_invalidating:
        lines += [
            "## ⚠ Risques invalidant la Classe A",
            "",
            "Les RSK suivants ont une sévérité `Critical` ou `Catastrophic`. La",
            "classification Class A est probablement incorrecte — revoir la",
            "classification avec le système qualité.",
            "",
        ] + [f"- {r}" for r in class_a_invalidating]

    return "\n".join(lines) + "\n", {
        "rsk_count": len(rsks),
        "rsk_unmitigated": unmitigated,
        "rsk_residual_unacceptable": residual_unacceptable,
        "rsk_class_a_invalidating": class_a_invalidating,
        "rsk_summary": summary,
    }


def build_cyber_risk_analysis(by_cat, controls_by_target, impl_by_srs, verif_by_srs):
    """Renvoie (markdown, dict d'analyse cyber)."""
    thrs = [t for t in by_cat["THR"] if t.status != "Deprecated"]

    lines = [
        "# Analyse de risques cyber (IEC 81001-5-1 / STRIDE)",
        "",
        f"_Généré le {date.today().isoformat()}_",
        "",
    ]

    if not thrs:
        lines += ["_(aucune menace enregistrée)_", ""]
        return "\n".join(lines), {
            "thr_count": 0,
            "thr_unmitigated": [],
            "thr_residual_unacceptable": [],
            "thr_high_risk": [],
            "thr_summary": [],
        }

    summary: list[dict] = []
    unmitigated: list[str] = []
    residual_unacceptable: list[str] = []
    high_risk: list[str] = []

    lines += [
        "## Synthèse",
        "",
        "| THR | Titre | STRIDE | Attaquant | Niveau | Initial OK | Résiduel OK | # Contrôles | RSK déclenchés |",
        "|---|---|---|---|---|---|---|---|---|",
    ]

    for thr in thrs:
        fm = thr.frontmatter
        stride = fm.get("stride") or []
        if isinstance(stride, str):
            stride = [stride]
        attacker = fm.get("attacker", "?")
        level = fm.get("risk_level", "Low")
        init_ok = bool(fm.get("acceptable", True))
        res_ok = bool(fm.get("residual_acceptable", True))
        controls = controls_by_target.get(thr.id, [])
        triggers = thr.links.get("triggers") or []

        if not init_ok and not controls:
            unmitigated.append(thr.id)
        if not res_ok:
            residual_unacceptable.append(thr.id)
        if level == "High" and not res_ok:
            high_risk.append(thr.id)

        summary.append({
            "id": thr.id,
            "title": thr.title,
            "stride": stride,
            "attacker": attacker,
            "level": level,
            "acceptable_initial": init_ok,
            "residual_acceptable": res_ok,
            "controls": [c.id for c in controls],
            "triggers": triggers,
        })

        lines.append(
            f"| {thr.id} | {thr.title} | {','.join(stride)} | {attacker} | "
            f"{level} | {'✓' if init_ok else '✗'} | {'✓' if res_ok else '✗'} | "
            f"{len(controls)} | {', '.join(triggers) or '—'} |"
        )

    lines += ["", "## Détail par THR", ""]

    for thr in thrs:
        fm = thr.frontmatter
        stride = fm.get("stride") or []
        if isinstance(stride, str):
            stride = [stride]
        lines.append(f"### {thr.id} — {thr.title}")
        lines.append("")
        lines.append(
            f"**Statut :** {thr.status} · **Version :** {fm.get('version', '?')}"
        )
        lines.append(
            f"**STRIDE :** {','.join(stride) or '?'} · "
            f"**Attaquant :** {fm.get('attacker', '?')} · "
            f"**Asset :** {fm.get('asset', '?')}"
        )
        lines.append(
            f"**Likelihood :** {fm.get('likelihood', '?')} · "
            f"**Impact :** {fm.get('impact', '?')} · "
            f"**Niveau :** {fm.get('risk_level', '?')}"
        )
        lines.append(
            f"**Acceptable (initial) :** "
            f"{'oui' if fm.get('acceptable', True) else 'non'} · "
            f"**Résiduel acceptable :** "
            f"{'oui' if fm.get('residual_acceptable', True) else 'non'}"
        )
        triggers = thr.links.get("triggers") or []
        if triggers:
            lines.append(f"**Déclenche (RSK) :** {', '.join(triggers)}")
        srcs = fm.get("source") or []
        if srcs:
            lines.append("**Source :** " + ", ".join(f"`{s}`" for s in srcs))
        lines.append("")

        controls = controls_by_target.get(thr.id, [])
        if controls:
            lines.append("**Contrôles :**")
            lines.append("")
            lines.append("| Item | Catégorie | Implémenté | Vérifié |")
            lines.append("|---|---|---|---|")
            for c in controls:
                if c.category == "SRS":
                    impl = "✓" if impl_by_srs.get(c.id) else "✗"
                    verif = "✓" if verif_by_srs.get(c.id) else "✗"
                elif c.category == "SDS":
                    impl = "✓ (design)"
                    verif = "n/a"
                else:
                    impl = "n/a"
                    verif = "✓ (test)"
                lines.append(f"| {c.id} | {c.category} | {impl} | {verif} |")
            lines.append("")
        else:
            lines.append("_Aucun contrôle enregistré._")
            lines.append("")
        lines.append(thr.body.strip())
        lines.append("")
        lines.append("---")
        lines.append("")

    if high_risk:
        lines += [
            "## ⚠ Threats à risque élevé non résolus",
            "",
            "Les THR suivants ont `risk_level: High` ET `residual_acceptable: false`.",
            "Renforcer les contrôles avant publication.",
            "",
        ] + [f"- {t}" for t in high_risk]

    return "\n".join(lines) + "\n", {
        "thr_count": len(thrs),
        "thr_unmitigated": unmitigated,
        "thr_residual_unacceptable": residual_unacceptable,
        "thr_high_risk": high_risk,
        "thr_summary": summary,
    }


def build_to_implement(by_cat, impl_by_srs, verif_by_srs, controls_by_target):
    """Backlog actionnable — structuré en groupes A/B/C/D."""
    srs = [s for s in by_cat["SRS"] if s.status != "Deprecated"]
    rsks = [r for r in by_cat["RSK"] if r.status != "Deprecated"]
    thrs = [t for t in by_cat["THR"] if t.status != "Deprecated"]

    # A. Safety (RSK)
    rsk_unmit = [
        r for r in rsks
        if not r.frontmatter.get("acceptable", True) and not controls_by_target.get(r.id)
    ]
    rsk_res_bad = [
        r for r in rsks if not r.frontmatter.get("residual_acceptable", True)
    ]

    # B. Cyber (THR)
    thr_unmit = [
        t for t in thrs
        if not t.frontmatter.get("acceptable", True) and not controls_by_target.get(t.id)
    ]
    thr_res_bad = [
        t for t in thrs if not t.frontmatter.get("residual_acceptable", True)
    ]

    # C. Mitigations à compléter (toutes catégories — RSK ou THR)
    mit_to_impl: list[Item] = []
    mit_to_verif: list[Item] = []
    for s in srs:
        if not s.mitigates:
            continue
        if not impl_by_srs.get(s.id):
            mit_to_impl.append(s)
        elif not verif_by_srs.get(s.id):
            mit_to_verif.append(s)

    # D. Autres exigences Must (hors mitigation)
    must_to_impl: list[Item] = []
    must_to_verif: list[Item] = []
    for s in srs:
        if s.frontmatter.get("priority", "Must") != "Must":
            continue
        if s.mitigates:
            continue
        if not impl_by_srs.get(s.id):
            must_to_impl.append(s)
        elif not verif_by_srs.get(s.id):
            must_to_verif.append(s)

    def _kind(targets: list[str]) -> str:
        has_rsk = any(t.startswith("RSK-") for t in targets)
        has_thr = any(t.startswith("THR-") for t in targets)
        if has_rsk and has_thr:
            return "mixed"
        if has_thr:
            return "cyber"
        return "safety"

    lines = [
        "# À implémenter — backlog actionnable",
        "",
        f"_Généré le {date.today().isoformat()}_",
        "",
        "> Source de vérité pour les actions concrètes. Régénéré à chaque",
        "> `python tools/build_docs.py`. Sections **BLOQUANT** = empêchent la",
        "> publication ; les autres sont informatives.",
        "",
        "---",
        "",
        "# A. Safety — ISO 14971 / IEC 62304 §7",
        "",
    ]

    def _section(title: str, rows: list[tuple[str, ...]], headers: tuple[str, ...]):
        lines.append(f"## {title}")
        lines.append("")
        if not rows:
            lines.append("_Rien à signaler._")
            lines.append("")
            return
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("|" + "|".join(["---"] * len(headers)) + "|")
        for r in rows:
            lines.append("| " + " | ".join(r) + " |")
        lines.append("")

    _section(
        "A.1 RSK sans contrôle (BLOQUANT)",
        [
            (
                r.id, r.title,
                r.frontmatter.get("severity", "?"),
                r.frontmatter.get("risk_level", "?"),
                "Définir au moins un contrôle (`links.mitigates`)",
            ) for r in rsk_unmit
        ],
        ("RSK", "Titre", "Sévérité", "Niveau", "Action"),
    )

    _section(
        "A.2 RSK avec résiduel non acceptable (BLOQUANT)",
        [
            (
                r.id, r.title,
                r.frontmatter.get("risk_level", "?"),
                "Renforcer les contrôles ou revoir la classification",
            ) for r in rsk_res_bad
        ],
        ("RSK", "Titre", "Niveau", "Action"),
    )

    lines += ["---", "", "# B. Cyber — IEC 81001-5-1 / STRIDE", ""]

    _section(
        "B.1 THR sans contrôle (BLOQUANT)",
        [
            (
                t.id, t.title,
                ",".join(t.frontmatter.get("stride") or []) or "?",
                t.frontmatter.get("risk_level", "?"),
                "Définir au moins un contrôle (`links.mitigates`)",
            ) for t in thr_unmit
        ],
        ("THR", "Titre", "STRIDE", "Niveau", "Action"),
    )

    _section(
        "B.2 THR avec résiduel non acceptable (BLOQUANT)",
        [
            (
                t.id, t.title,
                t.frontmatter.get("risk_level", "?"),
                "Renforcer les contrôles ou accepter le résiduel",
            ) for t in thr_res_bad
        ],
        ("THR", "Titre", "Niveau", "Action"),
    )

    lines += ["---", "", "# C. Mitigations à compléter (safety + cyber)", ""]

    _section(
        "C.1 Mitigations à implémenter (SRS sans SDS)",
        [
            (s.id, s.title, _kind(s.mitigates), ", ".join(s.mitigates),
             "Écrire le module qui réalise cette exigence")
            for s in mit_to_impl
        ],
        ("Mitigation SRS", "Titre", "Type", "Cible(s)", "Action"),
    )

    _section(
        "C.2 Mitigations à vérifier (SRS sans TC)",
        [
            (s.id, s.title, _kind(s.mitigates), ", ".join(s.mitigates),
             "Écrire un test de vérification")
            for s in mit_to_verif
        ],
        ("Mitigation SRS", "Titre", "Type", "Cible(s)", "Action"),
    )

    lines += ["---", "", "# D. Autres exigences Must", ""]

    _section(
        "D.1 À implémenter",
        [(s.id, s.title) for s in must_to_impl],
        ("SRS", "Titre"),
    )

    _section(
        "D.2 À vérifier",
        [(s.id, s.title) for s in must_to_verif],
        ("SRS", "Titre"),
    )

    nothing_left = not (
        rsk_unmit or rsk_res_bad or thr_unmit or thr_res_bad
        or mit_to_impl or mit_to_verif or must_to_impl or must_to_verif
    )
    if nothing_left:
        lines.append(
            "**Toutes les sections sont vides — la doc est en bon état pour publication.**"
        )
        lines.append("")

    return "\n".join(lines), {
        "rsk_unmitigated": [r.id for r in rsk_unmit],
        "rsk_residual_unacceptable": [r.id for r in rsk_res_bad],
        "thr_unmitigated": [t.id for t in thr_unmit],
        "thr_residual_unacceptable": [t.id for t in thr_res_bad],
        "mitigations_to_implement": [s.id for s in mit_to_impl],
        "mitigations_to_verify": [s.id for s in mit_to_verif],
        "must_to_implement": [s.id for s in must_to_impl],
        "must_to_verify": [s.id for s in must_to_verif],
        "nothing_left": nothing_left,
    }


def detect_test_frameworks() -> list[str]:
    """Inspecte les manifests pour lister les frameworks de test détectés."""
    found: list[str] = []
    pkg = ROOT / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            deps: dict[str, str] = {
                **(data.get("devDependencies") or {}),
                **(data.get("dependencies") or {}),
            }
            for name in (
                "vitest", "jest", "mocha", "ava",
                "playwright", "@playwright/test", "cypress",
                "@testing-library/react", "@testing-library/vue",
            ):
                if name in deps:
                    found.append(f"{name} ({deps[name]})")
        except Exception:  # noqa: BLE001 — JSON cassé : ne pas bloquer le build
            pass
    pyproj = ROOT / "pyproject.toml"
    py_text = ""
    if pyproj.exists():
        py_text += pyproj.read_text(encoding="utf-8")
    for r in ROOT.glob("requirements*.txt"):
        py_text += "\n" + r.read_text(encoding="utf-8")
    for name in ("pytest", "unittest", "tox", "hypothesis", "nose"):
        if re.search(rf"(^|[\s\"'\b])({re.escape(name)})([\s\"'\[<>=!~]|$)", py_text):
            found.append(name)
    return found


def read_test_plan_intro() -> dict[str, str]:
    """Parse `docs/test_plan_intro.md` ; renvoie {section_id: contenu}."""
    p = ROOT / "docs" / "test_plan_intro.md"
    if not p.exists():
        return {}
    text = p.read_text(encoding="utf-8")
    sections: dict[str, str] = {}
    cur_id: str | None = None
    cur_lines: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^##\s+([\w-]+)\s*$", line)
        if m:
            if cur_id is not None:
                sections[cur_id] = "\n".join(cur_lines).strip()
            cur_id = m.group(1)
            cur_lines = []
        elif cur_id is not None:
            cur_lines.append(line)
    if cur_id is not None:
        sections[cur_id] = "\n".join(cur_lines).strip()
    return sections


def build_std(by_cat) -> str:
    """Software Test Description — IEEE 829 / IEC 62304 §5.5/§5.7."""
    tcs = [t for t in by_cat["TC"] if t.status != "Deprecated"]
    srs = [s for s in by_cat["SRS"] if s.status != "Deprecated"]
    must = [s for s in srs if s.frontmatter.get("priority", "Must") == "Must"]

    by_level: dict[str, list[Item]] = defaultdict(list)
    for t in tcs:
        by_level[t.frontmatter.get("type", "Unit")].append(t)

    intro = read_test_plan_intro()
    frameworks = detect_test_frameworks()

    lines: list[str] = [
        "# Software Test Description (STD)",
        "",
        f"_Class A · IEC 62304 §5.5/§5.7 · IEEE 829 · "
        f"Généré le {date.today().isoformat()}_",
        "",
        "## 1. Introduction",
        "",
        "### 1.1 Objet",
        "",
        "Ce document décrit l'environnement, la stratégie et les cas de test",
        "pour la vérification du logiciel selon IEC 62304 §5.5 (vérification",
        "unitaire) et §5.7 (test système). Les cas de test sont produits depuis",
        "`docs/items/TC/` ; ce STD est régénéré à chaque build.",
        "",
        "### 1.2 Documents de référence",
        "",
        "- SRS — `docs/generated/10_SRS.md`",
        "- SDS — `docs/generated/20_SDS.md`",
        "- Matrice de traçabilité — `docs/generated/40_traceability.md`",
        "- Analyse de risques (safety) — `docs/generated/50_risk_analysis.md`",
        "- Analyse cyber — `docs/generated/60_cyber_risk_analysis.md`",
        "- IEC 62304:2006/AMD1:2015",
        "- IEEE 829-2008 (Standard for Software and System Test Documentation)",
        "",
        "### 1.3 Niveaux de test couverts",
        "",
    ]
    for lvl in ("Unit", "Integration", "System"):
        n = len(by_level.get(lvl, []))
        lines.append(f"- **{lvl}** — {n} TC")
    lines.append("")

    # 2. Environnement
    lines += ["## 2. Environnement de test", ""]
    if frameworks:
        lines.append("Frameworks détectés depuis les manifests :")
        lines.append("")
        for f in frameworks:
            lines.append(f"- {f}")
    else:
        lines.append(
            "_Aucun framework de test détecté automatiquement. Compléter via "
            "`docs/test_plan_intro.md`._"
        )
    lines.append("")

    # 3. Stratégie
    lines += ["## 3. Stratégie de test", ""]
    if intro.get("test-strategy"):
        lines.append(intro["test-strategy"])
    else:
        lines.append(
            "_[TODO] Renseigner la stratégie dans "
            "`docs/test_plan_intro.md` section `## test-strategy` "
            "(méthode, outillage, fréquence, automatisation)._"
        )
    lines.append("")

    # 4. Critères de pass/fail
    lines += ["## 4. Critères de pass/fail", ""]
    if intro.get("test-pass-fail"):
        lines.append(intro["test-pass-fail"])
    else:
        lines += [
            "- **PASS** — tous les TC vérifiant un SRS `priority: Must` sont",
            "  exécutés et passants ; aucun TC orphelin (sans `verifies`).",
            "- **FAIL** — ≥ 1 TC vérifiant un SRS Must est en échec.",
            "- **Skipped** — tracé dans le rapport, ne compte pas comme pass.",
        ]
    lines.append("")

    # 5. Couverture
    lines += [
        "## 5. Couverture",
        "",
        "| Niveau | # TC | SRS Must couverts |",
        "|---|---|---|",
    ]
    for lvl in ("Unit", "Integration", "System"):
        tcs_lvl = by_level.get(lvl, [])
        verifies_set: set[str] = set()
        for t in tcs_lvl:
            for sid in t.links.get("verifies") or []:
                verifies_set.add(sid)
        must_covered = sum(1 for s in must if s.id in verifies_set)
        rate = (must_covered / len(must)) if must else 0.0
        lines.append(
            f"| {lvl} | {len(tcs_lvl)} | {must_covered}/{len(must)} ({rate:.0%}) |"
        )
    lines.append("")

    # 6. Cas de test (table)
    lines += ["## 6. Cas de test", ""]
    section_idx = 0
    for lvl in ("Unit", "Integration", "System"):
        tcs_lvl = sorted(by_level.get(lvl, []), key=lambda x: x.id)
        if not tcs_lvl:
            continue
        section_idx += 1
        lines.append(f"### 6.{section_idx} {lvl}")
        lines.append("")
        lines.append("| ID | Titre | Vérifie | Auto |")
        lines.append("|---|---|---|---|")
        for t in tcs_lvl:
            verifies = ", ".join(t.links.get("verifies") or []) or "—"
            auto = t.frontmatter.get("automated", "?")
            lines.append(f"| {t.id} | {t.title} | {verifies} | {auto} |")
        lines.append("")

    # 7. Exclusions
    lines += ["## 7. Exclusions", ""]
    if intro.get("test-exclusions"):
        lines.append(intro["test-exclusions"])
    else:
        lines.append(
            "_[TODO] Renseigner les exclusions dans "
            "`docs/test_plan_intro.md` section `## test-exclusions` "
            "(composants non testés et justification)._"
        )
    lines.append("")

    # Annexe A — détail
    lines += ["---", "", "# Annexe A — Détail des cas de test", ""]
    if not tcs:
        lines += ["_(aucun TC enregistré)_", ""]
    for t in sorted(tcs, key=lambda x: x.id):
        lines.append(f"## {t.id} — {t.title}")
        lines.append("")
        lines.append(
            f"**Statut :** {t.status} · **Version :** "
            f"{t.frontmatter.get('version', '?')}"
        )
        lines.append(
            f"**Type :** {t.frontmatter.get('type', '?')} · "
            f"**Auto :** {t.frontmatter.get('automated', '?')}"
        )
        verif = t.links.get("verifies") or []
        if verif:
            lines.append(f"**Vérifie :** {', '.join(verif)}")
        mit = t.mitigates
        if mit:
            lines.append(f"**Mitige :** {', '.join(mit)}")
        srcs = t.frontmatter.get("source") or []
        if srcs:
            lines.append("**Source :** " + ", ".join(f"`{s}`" for s in srcs))
        lines.append("")
        lines.append(t.body.strip())
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def find_todo_markers() -> list[tuple[Path, int, str]]:
    hits: list[tuple[Path, int, str]] = []
    if not ITEMS_DIR.exists():
        return hits
    for path in ITEMS_DIR.rglob("*.md"):
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "[TODO]" in line or "[GAP-62304]" in line or "[GAP-CYBER]" in line:
                hits.append((path, n, line.strip()))
    return hits


def main() -> int:
    strict = "--strict" in sys.argv[1:]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    by_cat = load_items()
    impl_by_srs, verif_by_srs, controls_by_target = reverse_index(by_cat)

    (OUT_DIR / "10_SRS.md").write_text(
        render_aggregate(
            "Software Requirements Specification (SRS)", by_cat["SRS"], "SRS"
        ),
        encoding="utf-8",
    )
    (OUT_DIR / "20_SDS.md").write_text(
        render_aggregate(
            "Software Design Specification (SDS)", by_cat["SDS"], "SDS"
        ),
        encoding="utf-8",
    )
    (OUT_DIR / "30_STD.md").write_text(build_std(by_cat), encoding="utf-8")

    matrix_md, coverage = build_traceability(by_cat, impl_by_srs, verif_by_srs)
    (OUT_DIR / "40_traceability.md").write_text(matrix_md, encoding="utf-8")

    risk_md, risk_data = build_risk_analysis(
        by_cat, controls_by_target, impl_by_srs, verif_by_srs
    )
    (OUT_DIR / "50_risk_analysis.md").write_text(risk_md, encoding="utf-8")

    cyber_md, cyber_data = build_cyber_risk_analysis(
        by_cat, controls_by_target, impl_by_srs, verif_by_srs
    )
    (OUT_DIR / "60_cyber_risk_analysis.md").write_text(cyber_md, encoding="utf-8")

    todo_md, todo_data = build_to_implement(
        by_cat, impl_by_srs, verif_by_srs, controls_by_target
    )
    (OUT_DIR / "_to_implement.md").write_text(todo_md, encoding="utf-8")

    coverage["risks"] = risk_data
    coverage["threats"] = cyber_data
    coverage["to_implement"] = todo_data
    (OUT_DIR / "coverage.json").write_text(
        json.dumps(coverage, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(
        f"OK — items SRS={len(by_cat['SRS'])} SDS={len(by_cat['SDS'])} "
        f"TC={len(by_cat['TC'])} RSK={len(by_cat['RSK'])} THR={len(by_cat['THR'])}"
    )
    print(
        f"  impl={coverage['implementation_rate']:.0%} "
        f"verif_must={coverage['verification_rate_must']:.0%} "
        f"rsk_open={len(risk_data['rsk_unmitigated']) + len(risk_data['rsk_residual_unacceptable'])} "
        f"thr_open={len(cyber_data['thr_unmitigated']) + len(cyber_data['thr_residual_unacceptable'])}"
    )
    print(f"  → {OUT_DIR}")

    if strict:
        problems: list[str] = []
        todos = find_todo_markers()
        if todos:
            problems.append(
                f"{len(todos)} marqueur(s) [TODO]/[GAP-62304]/[GAP-CYBER]"
            )
            for path, n, line in todos:
                rel = path.relative_to(ROOT)
                print(f"  TODO {rel}:{n}: {line}", file=sys.stderr)
        if risk_data["rsk_class_a_invalidating"]:
            problems.append(
                f"{len(risk_data['rsk_class_a_invalidating'])} RSK avec sévérité "
                f"Critical/Catastrophic — Classe A invalide"
            )
        if risk_data["rsk_residual_unacceptable"]:
            problems.append(
                f"{len(risk_data['rsk_residual_unacceptable'])} RSK avec "
                f"residual_acceptable=false"
            )
        if risk_data["rsk_unmitigated"]:
            problems.append(
                f"{len(risk_data['rsk_unmitigated'])} RSK sans contrôle"
            )
        if cyber_data["thr_residual_unacceptable"]:
            problems.append(
                f"{len(cyber_data['thr_residual_unacceptable'])} THR avec "
                f"residual_acceptable=false"
            )
        if cyber_data["thr_unmitigated"]:
            problems.append(
                f"{len(cyber_data['thr_unmitigated'])} THR sans contrôle"
            )
        if problems:
            print("STRICT — problèmes :", file=sys.stderr)
            for p in problems:
                print(f"  - {p}", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
