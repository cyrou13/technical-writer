#!/usr/bin/env python3
"""
Build aggregated docs from the local item-store.

Reads `docs/items/<CAT>/*.md`, parses YAML frontmatter, produces:
  - docs/generated/10_SRS.md
  - docs/generated/20_SDS.md
  - docs/generated/30_STD.md                 (Software Test Description, IEEE 829)
  - docs/generated/40_traceability.md
  - docs/generated/50_risk_analysis.md       (safety - ISO 14971 / 62304 §7)
  - docs/generated/60_cyber_risk_analysis.md (cyber - IEC 81001-5-1 / STRIDE)
  - docs/generated/70_usability_analysis.md  (usability - IEC 62366-1)
  - docs/generated/_to_implement.md
  - docs/generated/coverage.json

Stdlib only.

Usage:
    python tools/build_docs.py [--strict]

`--strict` => exit != 0 if:
  - any [TODO], [GAP-62304], [GAP-CYBER] or [GAP-USE] marker,
  - any RSK or URSK with `severity: Critical|Catastrophic`,
  - any RSK / THR / URSK with `residual_acceptable: false`,
  - any RSK / THR / URSK with `acceptable: false` and no control.
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

CATEGORIES = ("MAP", "SRS", "SDS", "TC", "RSK", "THR", "USC", "URSK")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)

CLASS_A_INVALIDATING_SEVERITY = {"Critical", "Catastrophic"}

SEVERITY_INT: dict[str, int] = {
    "Negligible": 1,
    "Minor": 2,
    "Serious": 3,
    "Critical": 4,
    "Catastrophic": 5,
}
PROBABILITY_INT: dict[str, int] = {
    "Improbable": 1,
    "Remote": 2,
    "Occasional": 3,
    "Probable": 4,
    "Frequent": 5,
}


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
        return self.frontmatter.get("title", "(untitled)")

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
    if s in ("null", "Null", "NULL", "~"):
        return None
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
                print(f"WARN: no frontmatter in {path}", file=sys.stderr)
                continue
            fm = parse_yaml_frontmatter(m.group(1))
            body = m.group(2)
            item_id = fm.get("id") or path.stem
            if item_id != path.stem:
                print(
                    f"WARN: id {item_id} != filename {path.name}",
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
    """Compute reverse indexes:
    - impl_by_srs[srs_id]      = SDS IDs that implement
    - verif_by_srs[srs_id]     = TC IDs that verify
    - controls_by_target[id]   = Items (SRS/SDS/TC) that mitigate this RSK or THR
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
    lines = [f"# {title}", "", f"_Generated on {date.today().isoformat()}_", ""]
    if not items:
        lines += ["_(no item)_", ""]
        return "\n".join(lines)
    for it in items:
        if it.status == "Deprecated":
            continue
        lines.append(f"## {it.id} — {it.title}")
        lines.append("")
        lines.append(
            f"**Status:** {it.status} · **Version:** "
            f"{it.frontmatter.get('version', '?')}"
        )
        if category == "SRS":
            lines.append(
                f"**Verification:** {it.frontmatter.get('verification', '?')} · "
                f"**Priority:** {it.frontmatter.get('priority', '?')}"
            )
            mit = it.mitigates
            if mit:
                lines.append(f"**Mitigates:** {', '.join(mit)}")
        if category == "SDS":
            lines.append(f"**Module:** `{it.frontmatter.get('module', '?')}`")
            impls = it.links.get("implements") or []
            if impls:
                lines.append(f"**Implements:** {', '.join(impls)}")
            mit = it.mitigates
            if mit:
                lines.append(f"**Mitigates:** {', '.join(mit)}")
        if category == "TC":
            verif = it.links.get("verifies") or []
            lines.append(
                f"**Type:** {it.frontmatter.get('type', '?')} · "
                f"**Auto:** {it.frontmatter.get('automated', '?')}"
            )
            if verif:
                lines.append(f"**Verifies:** {', '.join(verif)}")
            mit = it.mitigates
            if mit:
                lines.append(f"**Mitigates:** {', '.join(mit)}")
        srcs = it.frontmatter.get("source") or []
        if srcs:
            lines.append("**Source:** " + ", ".join(f"`{s}`" for s in srcs))
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
        "# Traceability Matrix",
        "",
        f"_Generated on {date.today().isoformat()}_",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| SRS items (active) | {coverage['srs_count']} |",
        f"| SDS items (active) | {coverage['sds_count']} |",
        f"| TC items (active) | {coverage['tc_count']} |",
        f"| Implementation coverage | {impl_count}/{len(srs)} "
        f"({coverage['implementation_rate']:.0%}) |",
        f"| Verification coverage (Must) | {verif_must_count}/{len(must)} "
        f"({coverage['verification_rate_must']:.0%}) |",
        "",
        "## SRS → SDS → TC",
        "",
        "| SRS | Title | SDS | TC |",
        "|---|---|---|---|",
    ]
    for s in srs:
        sds_list = ", ".join(impl_by_srs[s.id]) or "—"
        tc_list = ", ".join(verif_by_srs[s.id]) or "—"
        lines.append(f"| {s.id} | {s.title} | {sds_list} | {tc_list} |")

    if coverage["orphans"]["sds"]:
        lines += ["", "## SDS without implemented requirement"]
        lines += [f"- {x}" for x in coverage["orphans"]["sds"]]
    if coverage["orphans"]["tc"]:
        lines += ["", "## TC with no verified requirement"]
        lines += [f"- {x}" for x in coverage["orphans"]["tc"]]

    return "\n".join(lines) + "\n", coverage


def build_risk_analysis(by_cat, controls_by_target, impl_by_srs, verif_by_srs):
    """Return (markdown, analysis dict for coverage and to_implement)."""
    rsks = [r for r in by_cat["RSK"] if r.status != "Deprecated"]

    lines = [
        "# Risk Analysis (IEC 62304 §7 — Class A)",
        "",
        f"_Generated on {date.today().isoformat()}_",
        "",
    ]

    if not rsks:
        lines += ["_(no risk registered)_", ""]
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
        "## Summary",
        "",
        "| RSK | Title | Severity | Level | Initial OK | Residual OK | # Controls |",
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

    lines += ["", "## Detail per RSK", ""]

    for rsk in rsks:
        fm = rsk.frontmatter
        lines.append(f"### {rsk.id} — {rsk.title}")
        lines.append("")

        # ISO 14971 category label
        risk_cat = fm.get("risk_category", "—")
        lines.append(f"**Category:** {risk_cat}")

        lines.append(
            f"**Status:** {rsk.status} · **Version:** {fm.get('version', '?')}"
        )

        # ISO 14971 §C.2 context
        sw_function = fm.get("software_function", "—")
        sw_item = fm.get("software_item", "—")
        lines.append(f"**Software function:** {sw_function}")
        lines.append(f"**Software item:** {sw_item}")

        lines.append(
            f"**Severity:** {fm.get('severity', '?')} · "
            f"**Probability:** {fm.get('probability', '?')} · "
            f"**Level:** {fm.get('risk_level', '?')}"
        )
        lines.append(
            f"**Acceptable (initial):** "
            f"{'yes' if fm.get('acceptable', True) else 'no'} · "
            f"**Residual acceptable:** "
            f"{'yes' if fm.get('residual_acceptable', True) else 'no'}"
        )

        # ISO 14971 §7.2 control hierarchy
        ctrl_hier = fm.get("control_hierarchy", "—")
        lines.append(f"**Control hierarchy:** {ctrl_hier}")

        srcs = fm.get("source") or []
        if srcs:
            lines.append("**Source:** " + ", ".join(f"`{s}`" for s in srcs))
        lines.append("")

        # Initiating causes (block scalar — preserve line breaks)
        if "initiating_causes" in fm:
            raw_causes = fm["initiating_causes"] or ""
            lines.append("**Initiating causes:**")
            lines.append("")
            for cause_line in str(raw_causes).splitlines():
                lines.append(cause_line)
            lines.append("")

        # Foreseeable sequence (block scalar — preserve line breaks)
        if "foreseeable_sequence" in fm:
            raw_seq = fm["foreseeable_sequence"] or ""
            lines.append("**Foreseeable sequence of events:**")
            lines.append("")
            for seq_line in str(raw_seq).splitlines():
                lines.append(seq_line)
            lines.append("")

        # Residual risk table
        res_prob = fm.get("residual_probability", "—")
        res_sev = fm.get("residual_severity", "—")
        res_level = fm.get("residual_risk_level", "—")
        lines.append("**Residual risk assessment:**")
        lines.append("")
        lines.append("| | Initial | Residual |")
        lines.append("|---|---|---|")
        lines.append(
            f"| Probability | {fm.get('probability', '—')} | {res_prob} |"
        )
        lines.append(
            f"| Severity | {fm.get('severity', '—')} | {res_sev} |"
        )
        lines.append(
            f"| Risk level | {fm.get('risk_level', '—')} | {res_level} |"
        )

        # Numerical risk index (P × S)
        init_sev_int = SEVERITY_INT.get(fm.get("severity", ""), 0)
        init_prob_int = PROBABILITY_INT.get(fm.get("probability", ""), 0)
        res_sev_int = SEVERITY_INT.get(res_sev, 0)
        res_prob_int = PROBABILITY_INT.get(res_prob, 0)
        if init_sev_int and init_prob_int:
            init_idx = init_sev_int * init_prob_int
            res_idx_str = (
                str(res_sev_int * res_prob_int)
                if res_sev_int and res_prob_int
                else "—"
            )
            lines.append(
                f"| Risk index (S×P) | {init_idx} | {res_idx_str} |"
            )
        lines.append("")

        # Arising risks (ISO 14971 §7.5)
        arising = fm.get("arising_risks") or []
        if arising:
            lines.append(
                "**Arising risks:** " + ", ".join(str(r) for r in arising)
            )
            lines.append("")

        # Labeling disclosure (ISO 14971 §7.6 / information_for_safety)
        labeling = fm.get("labeling_disclosure")
        if labeling is not None:
            lines.append("**Labeling disclosure:**")
            lines.append("")
            lines.append(str(labeling))
            lines.append("")

        controls = controls_by_target.get(rsk.id, [])
        if controls:
            lines.append("**Controls:**")
            lines.append("")
            lines.append("| Item | Category | Implemented | Verified |")
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
            lines.append("_No control registered._")
            lines.append("")
        lines.append(rsk.body.strip())
        lines.append("")
        lines.append("---")
        lines.append("")

    if class_a_invalidating:
        lines += [
            "## ⚠ Risks invalidating Class A",
            "",
            "The following RSKs have severity `Critical` or `Catastrophic`. The",
            "Class A classification is likely incorrect — review with the quality system.",
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
    """Return (markdown, cyber analysis dict)."""
    thrs = [t for t in by_cat["THR"] if t.status != "Deprecated"]

    lines = [
        "# Cyber Risk Analysis (IEC 81001-5-1 / STRIDE)",
        "",
        f"_Generated on {date.today().isoformat()}_",
        "",
    ]

    if not thrs:
        lines += ["_(no threat registered)_", ""]
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
        "## Summary",
        "",
        "| THR | Title | STRIDE | Attacker | Level | Initial OK | Residual OK | # Controls | Triggered RSK |",
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

    lines += ["", "## Detail per THR", ""]

    for thr in thrs:
        fm = thr.frontmatter
        stride = fm.get("stride") or []
        if isinstance(stride, str):
            stride = [stride]
        lines.append(f"### {thr.id} — {thr.title}")
        lines.append("")
        lines.append(
            f"**Status:** {thr.status} · **Version:** {fm.get('version', '?')}"
        )
        lines.append(
            f"**STRIDE:** {','.join(stride) or '?'} · "
            f"**Attacker:** {fm.get('attacker', '?')} · "
            f"**Asset:** {fm.get('asset', '?')}"
        )
        lines.append(
            f"**Likelihood:** {fm.get('likelihood', '?')} · "
            f"**Impact:** {fm.get('impact', '?')} · "
            f"**Level:** {fm.get('risk_level', '?')}"
        )
        lines.append(
            f"**Acceptable (initial):** "
            f"{'yes' if fm.get('acceptable', True) else 'no'} · "
            f"**Residual acceptable:** "
            f"{'yes' if fm.get('residual_acceptable', True) else 'no'}"
        )
        triggers = thr.links.get("triggers") or []
        if triggers:
            lines.append(f"**Triggers (RSK):** {', '.join(triggers)}")
        srcs = fm.get("source") or []
        if srcs:
            lines.append("**Source:** " + ", ".join(f"`{s}`" for s in srcs))
        lines.append("")

        controls = controls_by_target.get(thr.id, [])
        if controls:
            lines.append("**Controls:**")
            lines.append("")
            lines.append("| Item | Category | Implemented | Verified |")
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
            lines.append("_No control registered._")
            lines.append("")
        lines.append(thr.body.strip())
        lines.append("")
        lines.append("---")
        lines.append("")

    if high_risk:
        lines += [
            "## ⚠ Unresolved high-risk threats",
            "",
            "The following THRs have `risk_level: High` AND `residual_acceptable: false`.",
            "Strengthen controls before publication.",
            "",
        ] + [f"- {t}" for t in high_risk]

    return "\n".join(lines) + "\n", {
        "thr_count": len(thrs),
        "thr_unmitigated": unmitigated,
        "thr_residual_unacceptable": residual_unacceptable,
        "thr_high_risk": high_risk,
        "thr_summary": summary,
    }


def build_usability_analysis(by_cat, controls_by_target, impl_by_srs, verif_by_srs):
    """Return (markdown, usability analysis dict IEC 62366-1)."""
    uscs = [u for u in by_cat["USC"] if u.status != "Deprecated"]
    ursks = [r for r in by_cat["URSK"] if r.status != "Deprecated"]

    lines = [
        "# Usability Analysis (IEC 62366-1)",
        "",
        f"_Generated on {date.today().isoformat()}_",
        "",
    ]

    if not uscs and not ursks:
        lines += [
            "_No UI surface detected — IEC 62366-1 not applicable_",
            "",
        ]
        return "\n".join(lines), {
            "usc_count": 0,
            "ursk_count": 0,
            "ursk_unmitigated": [],
            "ursk_residual_unacceptable": [],
            "ursk_class_a_invalidating": [],
            "usc_summary": [],
            "ursk_summary": [],
        }

    # Section USC
    lines += ["## Use Scenarios (USC)", ""]
    if uscs:
        lines += [
            "| USC | Title | Persona | Environment | Task | Frequency | Criticality |",
            "|---|---|---|---|---|---|---|",
        ]
        for u in uscs:
            fm = u.frontmatter
            lines.append(
                f"| {u.id} | {u.title} | {fm.get('persona', '?')} | "
                f"{fm.get('environment', '?')} | {fm.get('task', '?')} | "
                f"{fm.get('frequency', '?')} | {fm.get('criticality', '?')} |"
            )
        lines.append("")
    else:
        lines += ["_(no USC registered)_", ""]

    # Section URSK
    ursk_unmit: list[str] = []
    ursk_res_bad: list[str] = []
    ursk_class_a_invalid: list[str] = []
    ursk_summary: list[dict] = []

    if ursks:
        lines += [
            "## Use-Related Risks (URSK)",
            "",
            "| URSK | Title | Persona-USC | Severity | Level | Initial OK | Residual OK | # Controls | Triggered RSK |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for r in ursks:
            fm = r.frontmatter
            sev = fm.get("severity", "Negligible")
            lvl = fm.get("risk_level", "Low")
            init_ok = bool(fm.get("acceptable", True))
            res_ok = bool(fm.get("residual_acceptable", True))
            controls = controls_by_target.get(r.id, [])
            triggers = r.links.get("triggers") or []
            usc_parent = fm.get("use_scenario", "—")

            if sev in CLASS_A_INVALIDATING_SEVERITY:
                ursk_class_a_invalid.append(r.id)
            if not init_ok and not controls:
                ursk_unmit.append(r.id)
            if not res_ok:
                ursk_res_bad.append(r.id)

            ursk_summary.append({
                "id": r.id,
                "title": r.title,
                "use_scenario": usc_parent,
                "severity": sev,
                "level": lvl,
                "acceptable_initial": init_ok,
                "residual_acceptable": res_ok,
                "controls": [c.id for c in controls],
                "triggers": triggers,
            })

            lines.append(
                f"| {r.id} | {r.title} | {usc_parent} | {sev} | {lvl} | "
                f"{'✓' if init_ok else '✗'} | {'✓' if res_ok else '✗'} | "
                f"{len(controls)} | {', '.join(triggers) or '—'} |"
            )
        lines.append("")
    else:
        lines += ["## Use-Related Risks (URSK)", "", "_(no URSK registered)_", ""]

    # Détail par USC
    if uscs:
        lines += ["## Detail per USC", ""]
        for u in uscs:
            fm = u.frontmatter
            lines.append(f"### {u.id} — {u.title}")
            lines.append("")
            lines.append(
                f"**Status:** {u.status} · **Version:** {fm.get('version', '?')}"
            )
            lines.append(
                f"**Persona:** {fm.get('persona', '?')} · "
                f"**Environment:** {fm.get('environment', '?')}"
            )
            lines.append(
                f"**Task:** {fm.get('task', '?')} · "
                f"**Frequency:** {fm.get('frequency', '?')} · "
                f"**Criticality:** {fm.get('criticality', '?')}"
            )
            srcs = fm.get("source") or []
            if srcs:
                lines.append("**Source:** " + ", ".join(f"`{s}`" for s in srcs))
            # linked URSKs
            children = [r for r in ursks if r.frontmatter.get("use_scenario") == u.id]
            if children:
                lines.append(
                    f"**Linked URSKs:** {', '.join(c.id for c in children)}"
                )
            lines.append("")
            lines.append(u.body.strip())
            lines.append("")
            lines.append("---")
            lines.append("")

    # Détail par URSK
    if ursks:
        lines += ["## Detail per URSK", ""]
        for r in ursks:
            fm = r.frontmatter
            lines.append(f"### {r.id} — {r.title}")
            lines.append("")
            lines.append(
                f"**Status:** {r.status} · **Version:** {fm.get('version', '?')}"
            )
            lines.append(
                f"**Parent USC:** {fm.get('use_scenario', '—')}"
            )
            lines.append(
                f"**Severity:** {fm.get('severity', '?')} · "
                f"**Likelihood:** {fm.get('likelihood', '?')} · "
                f"**Level:** {fm.get('risk_level', '?')}"
            )
            lines.append(
                f"**Acceptable (initial):** "
                f"{'yes' if fm.get('acceptable', True) else 'no'} · "
                f"**Residual acceptable:** "
                f"{'yes' if fm.get('residual_acceptable', True) else 'no'}"
            )
            triggers = r.links.get("triggers") or []
            if triggers:
                lines.append(f"**Triggers (RSK):** {', '.join(triggers)}")
            srcs = fm.get("source") or []
            if srcs:
                lines.append("**Source:** " + ", ".join(f"`{s}`" for s in srcs))
            lines.append("")

            controls = controls_by_target.get(r.id, [])
            if controls:
                lines.append("**Controls:**")
                lines.append("")
                lines.append("| Item | Category | Implemented | Verified |")
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
                lines.append("_No control registered._")
                lines.append("")
            lines.append(r.body.strip())
            lines.append("")
            lines.append("---")
            lines.append("")

    if ursk_class_a_invalid:
        lines += [
            "## ⚠ URSKs invalidating Class A",
            "",
            "The following URSKs have severity `Critical` or `Catastrophic`.",
            "A use error that can cause this level of harm challenges the",
            "Class A classification — review the classification.",
            "",
        ] + [f"- {u}" for u in ursk_class_a_invalid]

    return "\n".join(lines) + "\n", {
        "usc_count": len(uscs),
        "ursk_count": len(ursks),
        "ursk_unmitigated": ursk_unmit,
        "ursk_residual_unacceptable": ursk_res_bad,
        "ursk_class_a_invalidating": ursk_class_a_invalid,
        "usc_summary": [{"id": u.id, "title": u.title} for u in uscs],
        "ursk_summary": ursk_summary,
    }


def build_to_implement(by_cat, impl_by_srs, verif_by_srs, controls_by_target):
    """Actionable backlog — structured in groups A/B/C/D."""
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

    # C. Usability (URSK)
    ursks = [r for r in by_cat["URSK"] if r.status != "Deprecated"]
    ursk_unmit = [
        r for r in ursks
        if not r.frontmatter.get("acceptable", True) and not controls_by_target.get(r.id)
    ]
    ursk_res_bad = [
        r for r in ursks if not r.frontmatter.get("residual_acceptable", True)
    ]

    # D. Mitigations to complete (all categories — RSK, THR or URSK)
    mit_to_impl: list[Item] = []
    mit_to_verif: list[Item] = []
    for s in srs:
        if not s.mitigates:
            continue
        if not impl_by_srs.get(s.id):
            mit_to_impl.append(s)
        elif not verif_by_srs.get(s.id):
            mit_to_verif.append(s)

    # E. Other Must requirements (excluding mitigations)
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
        has_ursk = any(t.startswith("URSK-") for t in targets)
        kinds = []
        if has_rsk:
            kinds.append("safety")
        if has_thr:
            kinds.append("cyber")
        if has_ursk:
            kinds.append("usability")
        if not kinds:
            return "?"
        if len(kinds) == 1:
            return kinds[0]
        return "mixed(" + "+".join(kinds) + ")"

    lines = [
        "# To implement — actionable backlog",
        "",
        f"_Generated on {date.today().isoformat()}_",
        "",
        "> Source of truth for concrete actions. Regenerated on each",
        "> `python tools/build_docs.py`. **BLOCKING** sections prevent",
        "> publication; others are informational.",
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
            lines.append("_Nothing to report._")
            lines.append("")
            return
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("|" + "|".join(["---"] * len(headers)) + "|")
        for r in rows:
            lines.append("| " + " | ".join(r) + " |")
        lines.append("")

    _section(
        "A.1 RSK without control (BLOCKING)",
        [
            (
                r.id, r.title,
                r.frontmatter.get("severity", "?"),
                r.frontmatter.get("risk_level", "?"),
                "Define at least one control (`links.mitigates`)",
            ) for r in rsk_unmit
        ],
        ("RSK", "Title", "Severity", "Level", "Action"),
    )

    _section(
        "A.2 RSK with not acceptable residual (BLOCKING)",
        [
            (
                r.id, r.title,
                r.frontmatter.get("risk_level", "?"),
                "Strengthen controls or revise classification",
            ) for r in rsk_res_bad
        ],
        ("RSK", "Title", "Level", "Action"),
    )

    lines += ["---", "", "# B. Cyber — IEC 81001-5-1 / STRIDE", ""]

    _section(
        "B.1 THR without control (BLOCKING)",
        [
            (
                t.id, t.title,
                ",".join(t.frontmatter.get("stride") or []) or "?",
                t.frontmatter.get("risk_level", "?"),
                "Define at least one control (`links.mitigates`)",
            ) for t in thr_unmit
        ],
        ("THR", "Title", "STRIDE", "Level", "Action"),
    )

    _section(
        "B.2 THR with not acceptable residual (BLOCKING)",
        [
            (
                t.id, t.title,
                t.frontmatter.get("risk_level", "?"),
                "Strengthen controls or accept the residual",
            ) for t in thr_res_bad
        ],
        ("THR", "Title", "Level", "Action"),
    )

    lines += ["---", "", "# C. Usability — IEC 62366-1", ""]

    _section(
        "C.1 URSK without control (BLOCKING)",
        [
            (
                r.id, r.title,
                r.frontmatter.get("severity", "?"),
                r.frontmatter.get("risk_level", "?"),
                "Define at least one control (`links.mitigates`)",
            ) for r in ursk_unmit
        ],
        ("URSK", "Title", "Severity", "Level", "Action"),
    )

    _section(
        "C.2 URSK with not acceptable residual (BLOCKING)",
        [
            (
                r.id, r.title,
                r.frontmatter.get("risk_level", "?"),
                "Strengthen UI controls or accept the residual",
            ) for r in ursk_res_bad
        ],
        ("URSK", "Title", "Level", "Action"),
    )

    lines += ["---", "", "# D. Mitigations to complete (safety + cyber + usability)", ""]

    _section(
        "D.1 Mitigations to implement (SRS without SDS)",
        [
            (s.id, s.title, _kind(s.mitigates), ", ".join(s.mitigates),
             "Write the module that fulfils this requirement")
            for s in mit_to_impl
        ],
        ("Mitigation SRS", "Title", "Type", "Target(s)", "Action"),
    )

    _section(
        "D.2 Mitigations to verify (SRS without TC)",
        [
            (s.id, s.title, _kind(s.mitigates), ", ".join(s.mitigates),
             "Write a verification test")
            for s in mit_to_verif
        ],
        ("Mitigation SRS", "Title", "Type", "Target(s)", "Action"),
    )

    lines += ["---", "", "# E. Other Must requirements", ""]

    _section(
        "E.1 To implement",
        [(s.id, s.title) for s in must_to_impl],
        ("SRS", "Title"),
    )

    _section(
        "E.2 To verify",
        [(s.id, s.title) for s in must_to_verif],
        ("SRS", "Title"),
    )

    nothing_left = not (
        rsk_unmit or rsk_res_bad or thr_unmit or thr_res_bad
        or ursk_unmit or ursk_res_bad
        or mit_to_impl or mit_to_verif or must_to_impl or must_to_verif
    )
    if nothing_left:
        lines.append(
            "**All sections are empty — documentation is in good shape for publication.**"
        )
        lines.append("")

    return "\n".join(lines), {
        "rsk_unmitigated": [r.id for r in rsk_unmit],
        "rsk_residual_unacceptable": [r.id for r in rsk_res_bad],
        "thr_unmitigated": [t.id for t in thr_unmit],
        "thr_residual_unacceptable": [t.id for t in thr_res_bad],
        "ursk_unmitigated": [r.id for r in ursk_unmit],
        "ursk_residual_unacceptable": [r.id for r in ursk_res_bad],
        "mitigations_to_implement": [s.id for s in mit_to_impl],
        "mitigations_to_verify": [s.id for s in mit_to_verif],
        "must_to_implement": [s.id for s in must_to_impl],
        "must_to_verify": [s.id for s in must_to_verif],
        "nothing_left": nothing_left,
    }


def _scan_dirs_for_manifests() -> list[Path]:
    """Return bases to scan: ROOT + first-level git sub-repos.

    In a multi-repo setup (front/, back/, ...), each subdirectory containing
    a `.git/` is treated as an independent component.
    """
    bases = [ROOT]
    try:
        for child in sorted(ROOT.iterdir()):
            if child.is_dir() and (child / ".git").exists():
                bases.append(child)
    except OSError:
        pass
    return bases


def detect_test_frameworks() -> list[str]:
    """Inspect manifests to list detected test frameworks.

    In multi-repo mode, prefixes each entry with the component name
    (e.g. `front/: vitest 1.6.0`).
    """
    found: list[str] = []
    for base in _scan_dirs_for_manifests():
        prefix = "" if base == ROOT else f"{base.name}/: "
        pkg = base / "package.json"
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
                        found.append(f"{prefix}{name} ({deps[name]})")
            except Exception:  # noqa: BLE001 — JSON cassé : ne pas bloquer
                pass
        py_text = ""
        pyproj = base / "pyproject.toml"
        if pyproj.exists():
            py_text += pyproj.read_text(encoding="utf-8")
        for r in base.glob("requirements*.txt"):
            py_text += "\n" + r.read_text(encoding="utf-8")
        for name in ("pytest", "unittest", "tox", "hypothesis", "nose"):
            if re.search(
                rf"(^|[\s\"'\b])({re.escape(name)})([\s\"'\[<>=!~]|$)", py_text
            ):
                found.append(f"{prefix}{name}")
    return found


def read_test_plan_intro() -> dict[str, str]:
    """Parse `docs/test_plan_intro.md`; returns {section_id: content}."""
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
        f"Generated on {date.today().isoformat()}_",
        "",
        "## 1. Introduction",
        "",
        "### 1.1 Purpose",
        "",
        "This document describes the environment, strategy and test cases",
        "for software verification per IEC 62304 §5.5 (unit verification)",
        "and §5.7 (system test). Test cases are produced from",
        "`docs/items/TC/`; this STD is regenerated on each build.",
        "",
        "### 1.2 Reference documents",
        "",
        "- SRS — `docs/generated/10_SRS.md`",
        "- SDS — `docs/generated/20_SDS.md`",
        "- Traceability matrix — `docs/generated/40_traceability.md`",
        "- Risk analysis (safety) — `docs/generated/50_risk_analysis.md`",
        "- Cyber risk analysis — `docs/generated/60_cyber_risk_analysis.md`",
        "- IEC 62304:2006/AMD1:2015",
        "- IEEE 829-2008 (Standard for Software and System Test Documentation)",
        "",
        "### 1.3 Test levels covered",
        "",
    ]
    for lvl in ("Unit", "Integration", "System", "E2E"):
        n = len(by_level.get(lvl, []))
        lines.append(f"- **{lvl}** — {n} TC")
    lines.append("")

    # 2. Environment
    lines += ["## 2. Test environment", ""]
    if frameworks:
        lines.append("Frameworks detected from manifests:")
        lines.append("")
        for f in frameworks:
            lines.append(f"- {f}")
    else:
        lines.append(
            "_No test framework detected automatically. Complete via "
            "`docs/test_plan_intro.md`._"
        )
    lines.append("")

    # 3. Strategy
    lines += ["## 3. Test strategy", ""]
    if intro.get("test-strategy"):
        lines.append(intro["test-strategy"])
    else:
        lines.append(
            "_[TODO] Fill in the strategy in "
            "`docs/test_plan_intro.md` section `## test-strategy` "
            "(method, tooling, frequency, automation)._"
        )
    lines.append("")

    # 4. Pass/fail criteria
    lines += ["## 4. Pass/fail criteria", ""]
    if intro.get("test-pass-fail"):
        lines.append(intro["test-pass-fail"])
    else:
        lines += [
            "- **PASS** — all TCs verifying a `priority: Must` SRS are",
            "  executed and passing; no orphan TC (without `verifies`).",
            "- **FAIL** — >= 1 TC verifying a Must SRS is failing.",
            "- **Skipped** — recorded in the report, does not count as pass.",
        ]
    lines.append("")

    # 5. Coverage
    lines += [
        "## 5. Coverage",
        "",
        "| Level | # TC | SRS Must covered |",
        "|---|---|---|",
    ]
    for lvl in ("Unit", "Integration", "System", "E2E"):
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

    # 6. Test cases (table)
    lines += ["## 6. Test cases", ""]
    section_idx = 0
    for lvl in ("Unit", "Integration", "System", "E2E"):
        tcs_lvl = sorted(by_level.get(lvl, []), key=lambda x: x.id)
        if not tcs_lvl:
            continue
        section_idx += 1
        lines.append(f"### 6.{section_idx} {lvl}")
        lines.append("")
        lines.append("| ID | Title | Verifies | Auto |")
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
            "_[TODO] Fill in exclusions in "
            "`docs/test_plan_intro.md` section `## test-exclusions` "
            "(untested components and justification)._"
        )
    lines.append("")

    # Annex A — detail
    lines += ["---", "", "# Annex A — Test case detail", ""]
    if not tcs:
        lines += ["_(no TC registered)_", ""]
    for t in sorted(tcs, key=lambda x: x.id):
        lines.append(f"## {t.id} — {t.title}")
        lines.append("")
        lines.append(
            f"**Status:** {t.status} · **Version:** "
            f"{t.frontmatter.get('version', '?')}"
        )
        lines.append(
            f"**Type:** {t.frontmatter.get('type', '?')} · "
            f"**Auto:** {t.frontmatter.get('automated', '?')}"
        )
        verif = t.links.get("verifies") or []
        if verif:
            lines.append(f"**Verifies:** {', '.join(verif)}")
        mit = t.mitigates
        if mit:
            lines.append(f"**Mitigates:** {', '.join(mit)}")
        srcs = t.frontmatter.get("source") or []
        if srcs:
            lines.append("**Source:** " + ", ".join(f"`{s}`" for s in srcs))
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
            if (
                "[TODO]" in line
                or "[GAP-62304]" in line
                or "[GAP-CYBER]" in line
                or "[GAP-USE]" in line
            ):
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

    use_md, use_data = build_usability_analysis(
        by_cat, controls_by_target, impl_by_srs, verif_by_srs
    )
    (OUT_DIR / "70_usability_analysis.md").write_text(use_md, encoding="utf-8")

    todo_md, todo_data = build_to_implement(
        by_cat, impl_by_srs, verif_by_srs, controls_by_target
    )
    (OUT_DIR / "_to_implement.md").write_text(todo_md, encoding="utf-8")

    coverage["risks"] = risk_data
    coverage["threats"] = cyber_data
    coverage["usability"] = use_data
    coverage["to_implement"] = todo_data
    (OUT_DIR / "coverage.json").write_text(
        json.dumps(coverage, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print(
        f"OK — items SRS={len(by_cat['SRS'])} SDS={len(by_cat['SDS'])} "
        f"TC={len(by_cat['TC'])} RSK={len(by_cat['RSK'])} "
        f"THR={len(by_cat['THR'])} USC={len(by_cat['USC'])} URSK={len(by_cat['URSK'])}"
    )
    print(
        f"  impl={coverage['implementation_rate']:.0%} "
        f"verif_must={coverage['verification_rate_must']:.0%} "
        f"rsk_open={len(risk_data['rsk_unmitigated']) + len(risk_data['rsk_residual_unacceptable'])} "
        f"thr_open={len(cyber_data['thr_unmitigated']) + len(cyber_data['thr_residual_unacceptable'])} "
        f"ursk_open={len(use_data['ursk_unmitigated']) + len(use_data['ursk_residual_unacceptable'])}"
    )
    print(f"  → {OUT_DIR}")

    if strict:
        problems: list[str] = []
        todos = find_todo_markers()
        if todos:
            problems.append(
                f"{len(todos)} marker(s) [TODO]/[GAP-62304]/[GAP-CYBER]/[GAP-USE]"
            )
            for path, n, line in todos:
                rel = path.relative_to(ROOT)
                print(f"  TODO {rel}:{n}: {line}", file=sys.stderr)
        if risk_data["rsk_class_a_invalidating"]:
            problems.append(
                f"{len(risk_data['rsk_class_a_invalidating'])} RSK with severity "
                f"Critical/Catastrophic — Class A invalid"
            )
        if risk_data["rsk_residual_unacceptable"]:
            problems.append(
                f"{len(risk_data['rsk_residual_unacceptable'])} RSK with "
                f"residual_acceptable=false"
            )
        if risk_data["rsk_unmitigated"]:
            problems.append(
                f"{len(risk_data['rsk_unmitigated'])} RSK without control"
            )
        if cyber_data["thr_residual_unacceptable"]:
            problems.append(
                f"{len(cyber_data['thr_residual_unacceptable'])} THR with "
                f"residual_acceptable=false"
            )
        if cyber_data["thr_unmitigated"]:
            problems.append(
                f"{len(cyber_data['thr_unmitigated'])} THR without control"
            )
        if use_data["ursk_class_a_invalidating"]:
            problems.append(
                f"{len(use_data['ursk_class_a_invalidating'])} URSK with severity "
                f"Critical/Catastrophic — Class A invalid"
            )
        if use_data["ursk_residual_unacceptable"]:
            problems.append(
                f"{len(use_data['ursk_residual_unacceptable'])} URSK with "
                f"residual_acceptable=false"
            )
        if use_data["ursk_unmitigated"]:
            problems.append(
                f"{len(use_data['ursk_unmitigated'])} URSK without control"
            )
        if problems:
            print("STRICT — problems:", file=sys.stderr)
            for p in problems:
                print(f"  - {p}", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
