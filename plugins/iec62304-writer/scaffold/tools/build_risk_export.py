#!/usr/bin/env python3
"""Build the QMS-ready Risk Analysis Report deliverable.

Equivalent of the Avicenna AV-DP-XXX-10-005-annex2-RISK-REPORT.docx
(plus a simplified flat CSV equivalent of annex1-RISK-TABLE.xlsx).

Reads:
    dt-config.yaml
    docs/dt-clinical-context.md  (needs `## end-users` and
                                   `## characteristics-affecting-safety`
                                   anchors in addition to the SRS ones)
    docs/items/RSK/*.md          (required — error if empty)
    docs/items/THR/*.md          (optional — cyber design assessment)
    docs/items/URSK/*.md         (optional — included in CSV inventory)
    docs/items/{SRS,SDS,TC}/*.md (optional — to enumerate mitigating items)

Writes:
    docs/export/<id>-<v>-RISK-REPORT.md
    docs/export/<id>-<v>-RISK-REPORT.docx  (if pandoc + reference_docx)
    docs/export/<id>-<v>-RISK-TABLE.csv
    docs/export/<id>-<v>-risk-export.log

Stdlib only. Python 3.12+.
"""

from __future__ import annotations

import argparse
import csv
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
    Item,
    load_clinical_context,
    load_items,
    parse_yaml,
    risk_index,
    section_or_todo,
)

ROOT = Path.cwd()
CONFIG_PATH = ROOT / "dt-config.yaml"
CLINICAL_PATH = ROOT / "docs" / "dt-clinical-context.md"
ITEMS_DIR = ROOT / "docs" / "items"
EXPORT_DIR = ROOT / "docs" / "export"


CLASS_A_INVALIDATING = {"Critical", "Catastrophic"}


# ---------------------------------------------------------------------------
# BuildContext + Markdown builders
# ---------------------------------------------------------------------------


@dataclass
class BuildContext:
    config: dict
    clinical: dict[str, str]
    rsk: list[Item]
    thr: list[Item]
    ursk: list[Item]
    prsk: list[Item] = field(default_factory=list)
    # Items whose links.mitigates point at a risk — used to enumerate controls.
    mitigators: list[Item] = field(default_factory=list)
    log_lines: list[str] = field(default_factory=list)

    def log(self, msg: str) -> None:
        self.log_lines.append(msg)
        print(msg, file=sys.stderr)

    def controls_for(self, risk_id: str) -> list[Item]:
        return [m for m in self.mitigators if risk_id in m.mitigates]


def fmt_signatory(ctx: BuildContext, role: str) -> str:
    approvals = (ctx.config.get("approvals") or {}) if ctx.config else {}
    entry = approvals.get(role) or {}
    name = entry.get("name") or "[TODO]"
    job = entry.get("role") or "[TODO]"
    return f"{name} — {job}"


def build_cover(ctx: BuildContext) -> list[str]:
    doc = (ctx.config.get("document") or {}) if ctx.config else {}
    title = doc.get("title") or "[TODO document.title]"
    base_title = re.sub(r"\bSoftware Requirements Specification\b", "Risk Analysis Report", str(title))
    if base_title == title:
        base_title = f"{title} — Risk Analysis Report"
    identifier = doc.get("identifier") or "[TODO document.identifier]"
    risk_identifier = identifier.replace("SRS", "RAR") if "SRS" in identifier else f"{identifier}-RAR"
    version_label = doc.get("version_label") or "V01"
    date = doc.get("date") or "[TODO document.date]"
    return [
        f"# {base_title}",
        "",
        f"**Document identifier:** {risk_identifier}  ",
        f"**Version:** {version_label}  ",
        f"**Date:** {date}",
        "",
        "## Signatures",
        "",
        "| Role | Name and role | Date |",
        "|---|---|---|",
        f"| Written by | {fmt_signatory(ctx, 'written_by')} | {date} |",
        f"| Verified by | {fmt_signatory(ctx, 'verified_by')} | {date} |",
        f"| Approved by | {fmt_signatory(ctx, 'approved_by')} | {date} |",
        "",
    ]


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
    lines += ["", "---", ""]
    return lines


def build_introduction(ctx: BuildContext) -> list[str]:
    refs = ctx.config.get("project_references") or [] if ctx.config else []
    lines = [
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
            lines.append(
                f"| [{r.get('id') or 'R?'}] | {r.get('identifier') or '[TODO]'} "
                f"| {r.get('title') or '[TODO]'} |"
            )
    else:
        lines.append("_(no project references configured)_")
    lines += [
        "",
        "## 1.4 Conventions",
        "",
        "Risk items follow ISO 14971:2019 §C.2 — every item documents the full",
        "causal chain (initiating causes → foreseeable sequence → hazardous",
        "situation → harm) and the ISO 14971 §7.2 control hierarchy",
        "(inherent_design > protective_measure > information_for_safety).",
        "",
        "The risk index is computed as `severity × probability` per the",
        "ranking system in §2.4 below.",
        "",
        "---",
        "",
    ]
    return lines


def build_ranking_table(_ctx: BuildContext) -> list[str]:
    return [
        "## 2.4 Risk Level (RL) Ranking",
        "",
        "Probability mapping:",
        "",
        "| Probability | Int |",
        "|---|---|",
        "| Improbable | 1 |",
        "| Remote | 2 |",
        "| Occasional | 3 |",
        "| Probable | 4 |",
        "| Frequent | 5 |",
        "",
        "Severity mapping:",
        "",
        "| Severity | Int |",
        "|---|---|",
        "| Negligible | 1 |",
        "| Minor | 2 |",
        "| Serious | 3 |",
        "| Critical | 4 |",
        "| Catastrophic | 5 |",
        "",
        "Risk index = severity × probability. Risk level matrix:",
        "",
        "| Index | Risk Level |",
        "|---|---|",
        "| 1 – 4 | Low |",
        "| 5 – 12 | Medium |",
        "| 13 – 25 | High |",
        "",
    ]


def classify_software(ctx: BuildContext) -> tuple[str, list[str]]:
    """Return (classification_text, list_of_offending_rsk_ids)."""
    offenders: list[str] = []
    for r in ctx.rsk:
        if r.status == "Deprecated":
            continue
        for field_name in ("severity", "residual_severity"):
            val = r.get(field_name)
            if val in CLASS_A_INVALIDATING:
                offenders.append(f"{r.id} (`{field_name}={val}`)")
    if not offenders:
        return ("IEC 62304 Class A — all identified hazards have severity ≤ Serious, both initial and residual.", [])
    return (
        "⚠ Class B/C escalation required — the following RSK items have severity Critical or Catastrophic:",
        offenders,
    )


def render_risk_detail(ctx: BuildContext, r: Item) -> list[str]:
    sev = r.get("severity")
    prob = r.get("probability")
    idx = risk_index(sev, prob)
    rsev = r.get("residual_severity")
    rprob = r.get("residual_probability")
    ridx = risk_index(rsev, rprob)

    controls = ctx.controls_for(r.id)
    controls_str = ", ".join(c.id for c in controls) if controls else "(none yet)"

    arising = r.get("arising_risks") or []
    arising_str = ", ".join(arising) if arising else "none"

    labeling = r.get("labeling_disclosure")

    lines = [
        f"### {r.id} — {r.title}",
        "",
        f"- **Category:** {r.get('risk_category') or '—'}",
        f"- **Software function:** {r.get('software_function') or '—'}",
        f"- **Software item:** {r.get('software_item') or '—'}",
        f"- **Hazard:** {r.get('hazard') or '[TODO]'}",
        "",
        "**Initiating causes:**",
        "",
        str(r.get("initiating_causes") or "[TODO]"),
        "",
        "**Foreseeable sequence of events:**",
        "",
        str(r.get("foreseeable_sequence") or "[TODO]"),
        "",
        f"- **Hazardous situation:** {r.get('hazardous_situation') or '[TODO]'}",
        f"- **Harm:** {r.get('harm') or '[TODO]'}",
        "",
        f"- **Initial risk:** severity=`{sev or '—'}` · probability=`{prob or '—'}` · "
        f"index=`{idx if idx is not None else '—'}` · level=`{r.get('risk_level') or '—'}` · "
        f"acceptable=`{r.get('acceptable')}`",
        f"- **Control hierarchy:** `{r.get('control_hierarchy') or '—'}`",
        f"- **Mitigating items:** {controls_str}",
        f"- **Residual risk:** severity=`{rsev or '—'}` · probability=`{rprob or '—'}` · "
        f"index=`{ridx if ridx is not None else '—'}` · level=`{r.get('residual_risk_level') or '—'}` · "
        f"acceptable=`{r.get('residual_acceptable')}`",
        f"- **Arising risks:** {arising_str}",
    ]
    if labeling and labeling != "null":
        lines += ["", "**Labeling disclosure (IFU verbatim):**", "", f"> {labeling}"]
    lines.append("")
    return lines


def render_threat_detail(_ctx: BuildContext, t: Item) -> list[str]:
    # CIA fields — defensive get for backward compatibility with pre-CIA items
    c_sev = t.get("confidentiality_severity") or "—"
    i_sev = t.get("integrity_severity") or "—"
    a_sev = t.get("availability_severity") or "—"
    rc_sev = t.get("residual_confidentiality_severity") or "—"
    ri_sev = t.get("residual_integrity_severity") or "—"
    ra_sev = t.get("residual_availability_severity") or "—"
    return [
        f"### {t.id} — {t.title}",
        "",
        f"- **STRIDE:** {t.get('stride') or '—'}",
        f"- **Attacker:** {t.get('attacker') or '—'}",
        f"- **Asset:** {t.get('asset') or '—'}",
        f"- **Likelihood:** {t.get('likelihood') or '—'} · **Impact:** {t.get('impact') or '—'} · "
        f"**Level:** {t.get('risk_level') or '—'} · **Acceptable:** {t.get('acceptable')}",
        f"- **Residual acceptable:** {t.get('residual_acceptable')}",
        "",
        "**CIA impact (IEC 81001-5-1):**",
        "",
        "| Dimension | Initial | Residual |",
        "|---|---|---|",
        f"| Confidentiality | {c_sev} | {rc_sev} |",
        f"| Integrity | {i_sev} | {ri_sev} |",
        f"| Availability | {a_sev} | {ra_sev} |",
        "",
    ]


def build_risk_section(ctx: BuildContext) -> list[str]:
    active = [r for r in ctx.rsk if r.status != "Deprecated"]
    classification_text, offenders = classify_software(ctx)

    lines = [
        "# 2. Risk analysis (ISO 14971 / IEC 62304 §7)",
        "",
        "## 2.1 Intended use",
        "",
        section_or_todo(ctx.clinical, "intended-use"),
        "",
        "## 2.2 End users",
        "",
        section_or_todo(ctx.clinical, "end-users"),
        "",
        "## 2.3 Characteristics Affecting Safety",
        "",
        section_or_todo(ctx.clinical, "characteristics-affecting-safety"),
        "",
    ]
    lines += build_ranking_table(ctx)
    lines += [
        "## 2.5 Software safety classification",
        "",
        classification_text,
        "",
    ]
    if offenders:
        for line in offenders:
            lines.append(f"- {line}")
        lines.append("")

    lines += ["## 2.6 Risk analysis and evaluation", ""]
    if not active:
        lines += ["_(no active RSK items)_", ""]
    else:
        for r in sorted(active, key=lambda r: r.id):
            lines += render_risk_detail(ctx, r)

    # 2.7 Generation of Other Hazards (arising_risks cascade)
    cascades = [(r, r.get("arising_risks") or []) for r in active]
    cascades = [(r, ar) for r, ar in cascades if ar]
    lines += ["## 2.7 Generation of Other Hazards (ISO 14971 §7.5)", ""]
    if not cascades:
        lines += ["_(no cascading risks recorded)_", ""]
    else:
        lines += ["| Parent RSK | Arising risk IDs |", "|---|---|"]
        for r, ar in cascades:
            lines.append(f"| {r.id} | {', '.join(ar)} |")
        lines.append("")

    # 2.8 Residual risk evaluation
    n_total = len(active)
    n_initially_ok = sum(1 for r in active if r.get("acceptable") is True)
    n_reduced = sum(
        1
        for r in active
        if r.get("acceptable") is False and r.get("residual_acceptable") is True
    )
    n_not_acceptable = sum(1 for r in active if r.get("residual_acceptable") is False)
    lines += [
        "## 2.8 Residual risk evaluation",
        "",
        f"- Total active RSK: **{n_total}**",
        f"- Initially acceptable (no mitigation needed): **{n_initially_ok}**",
        f"- Reduced to acceptable via controls: **{n_reduced}**",
        f"- Still NOT acceptable after mitigation ⚠: **{n_not_acceptable}**",
        "",
    ]
    if n_not_acceptable:
        lines.append("Items requiring further mitigation:")
        lines.append("")
        for r in active:
            if r.get("residual_acceptable") is False:
                lines.append(f"- ⚠ `{r.id}` — {r.title}")
        lines.append("")

    lines += [
        "## 2.9 Adequacy of Device Safety and benefit-risk analysis",
        "",
        "[TODO — human judgement required. This section asserts that the",
        "clinical benefit outweighs the residual risks (ISO 14971 §8). It",
        "cannot be auto-generated. The RAQA / Regulatory Manager must",
        "complete and sign this section before submission.]",
        "",
        "---",
        "",
    ]
    return lines


def render_prsk_detail(ctx: BuildContext, p: Item) -> list[str]:
    sev = p.get("severity")
    prob = p.get("probability")
    idx = risk_index(sev, prob)
    rsev = p.get("residual_severity")
    rprob = p.get("residual_probability")
    ridx = risk_index(rsev, rprob)

    controls = ctx.controls_for(p.id)
    controls_str = ", ".join(c.id for c in controls) if controls else "(none yet)"

    return [
        f"### {p.id} — {p.title}",
        "",
        f"- **Production phase:** {p.get('production_phase') or '—'}",
        f"- **Asset at risk:** {p.get('asset_at_risk') or '—'}",
        f"- **Hazard:** {p.get('hazard') or '[TODO]'}",
        "",
        "**Initiating causes:**",
        "",
        str(p.get("initiating_causes") or "[TODO]"),
        "",
        "**Foreseeable sequence of events:**",
        "",
        str(p.get("foreseeable_sequence") or "[TODO]"),
        "",
        f"- **Hazardous situation:** {p.get('hazardous_situation') or '[TODO]'}",
        f"- **Harm:** {p.get('harm') or '[TODO]'}",
        "",
        f"- **Initial risk:** severity=`{sev or '—'}` · probability=`{prob or '—'}` · "
        f"index=`{idx if idx is not None else '—'}` · level=`{p.get('risk_level') or '—'}` · "
        f"acceptable=`{p.get('acceptable')}`",
        f"- **Control hierarchy:** `{p.get('control_hierarchy') or '—'}`",
        f"- **Mitigating items:** {controls_str}",
        f"- **Residual risk:** severity=`{rsev or '—'}` · probability=`{rprob or '—'}` · "
        f"index=`{ridx if ridx is not None else '—'}` · level=`{p.get('residual_risk_level') or '—'}` · "
        f"acceptable=`{p.get('residual_acceptable')}`",
        "",
    ]


def build_production_section(ctx: BuildContext) -> list[str]:
    active = [p for p in ctx.prsk if p.status != "Deprecated"]
    lines = [
        "## 2.10 Production risk analysis (AAMI TIR57 / IEC 81001-5-1 §6.1)",
        "",
        "Production risks cover the window between build and deployment:",
        "packaging integrity, signing, delivery, deployment, and update",
        "phases. Distinct from runtime design risks (§2.6) and from cyber",
        "threats against the running application (§3).",
        "",
    ]
    if not active:
        lines += [
            "_(no active PRSK items — production phase may not be applicable to this project)_",
            "",
            "---",
            "",
        ]
        return lines
    for p in sorted(active, key=lambda i: i.id):
        lines += render_prsk_detail(ctx, p)
    lines += ["---", ""]
    return lines


def build_cyber_section(ctx: BuildContext) -> list[str]:
    active = [t for t in ctx.thr if t.status != "Deprecated"]
    lines = ["# 3. Cybersecurity risk analysis", "", "## 3.1 Design risk assessment", ""]
    if not active:
        lines += ["_(no active THR items — see `/doc-62304` to generate from code)_", ""]
    else:
        for t in sorted(active, key=lambda t: t.id):
            lines += render_threat_detail(ctx, t)
    lines += [
        "## 3.2 Production risk assessment",
        "",
        "[TODO — describe production-phase cyber risks: CI/CD pipeline integrity,",
        "supply chain (npm/pypi/docker registry), signing keys management, secret",
        "rotation, deployment artifact provenance (SBOM, signed images).]",
        "",
        "## 3.3 Post-production risk assessment",
        "",
        "[TODO — describe the post-production cyber risk management process:",
        "SBOM-based vulnerability scanning cadence, coordinated vulnerability",
        "disclosure (CVD) policy, post-market monitoring, end-of-support",
        "transition.]",
        "",
        "---",
        "",
    ]
    return lines


def build_conclusion(ctx: BuildContext) -> list[str]:
    active_rsk = [r for r in ctx.rsk if r.status != "Deprecated"]
    active_thr = [t for t in ctx.thr if t.status != "Deprecated"]
    active_prsk = [p for p in ctx.prsk if p.status != "Deprecated"]
    n_prsk = len(active_prsk)
    n_prsk_blocked = sum(1 for p in active_prsk if p.get("residual_acceptable") is False)
    n_rsk = len(active_rsk)
    n_rsk_ok_initial = sum(1 for r in active_rsk if r.get("acceptable") is True)
    n_rsk_mitigated = sum(
        1
        for r in active_rsk
        if r.get("acceptable") is False and r.get("residual_acceptable") is True
    )
    n_rsk_blocked = sum(1 for r in active_rsk if r.get("residual_acceptable") is False)
    n_thr = len(active_thr)
    n_thr_blocked = sum(1 for t in active_thr if t.get("residual_acceptable") is False)
    return [
        "# 4. Conclusion",
        "",
        "## 4.1 Risks evaluation strategy",
        "",
        "Methodology applied:",
        "",
        "- **ISO 14971:2019** for safety risk management (§C.2 causal chain, §7.2",
        "  control hierarchy, §7.4 residual risk, §7.5 cascade, §7.6 labeling).",
        "- **IEC 62304** §7 for software-of-medical-device risk activities.",
        "- **IEC 81001-5-1** for cybersecurity risk management (where THR items",
        "  are produced — see §3).",
        "- **AAMI TIR57 / IEC 81001-5-1 §6.1** for production-phase risks",
        "  (PRSK items — see §2.10).",
        "",
        "Risk index = severity × probability, mapped to Low/Medium/High via the",
        "matrix in §2.4.",
        "",
        "## 4.2 Risk Management Analysis",
        "",
        f"- Total safety risks (RSK) identified: **{n_rsk}**",
        f"- RSK initially acceptable (no mitigation needed): **{n_rsk_ok_initial}**",
        f"- RSK reduced to acceptable via controls: **{n_rsk_mitigated}**",
        f"- RSK still NOT acceptable after mitigation ⚠: **{n_rsk_blocked}**",
        f"- Total production risks (PRSK) identified: **{n_prsk}**",
        f"- PRSK still NOT acceptable after mitigation ⚠: **{n_prsk_blocked}**",
        f"- Total cyber threats (THR) identified: **{n_thr}**",
        f"- THR still NOT acceptable after mitigation ⚠: **{n_thr_blocked}**",
        "",
        "## 4.3 Benefit/Risk analysis",
        "",
        "[TODO — human judgement required. Insert verbatim from the QMS",
        "Benefit-Risk Analysis document. ISO 14971 §8: the manufacturer asserts",
        "that the clinical benefit outweighs the residual risks. Cannot be",
        "auto-generated from code. Signed by the Regulatory Manager.]",
        "",
    ]


def render_markdown(ctx: BuildContext) -> str:
    parts: list[str] = []
    parts += build_cover(ctx)
    parts += build_revision_history(ctx)
    parts += build_introduction(ctx)
    parts += build_risk_section(ctx)
    parts += build_production_section(ctx)
    parts += build_cyber_section(ctx)
    parts += build_conclusion(ctx)
    return "\n".join(parts).rstrip() + "\n"


# ---------------------------------------------------------------------------
# CSV inventory
# ---------------------------------------------------------------------------


CSV_HEADER = [
    "Risk ID",
    "Risk Category",
    "Software Function",
    "Software Item",
    "Hazard",
    "Initiating Causes",
    "Foreseeable Sequence",
    "Hazardous Situation",
    "Harm",
    "Initial Severity",
    "Initial Probability",
    "Initial Risk Level",
    "Control Hierarchy",
    "Mitigating Items",
    "Residual Severity",
    "Residual Probability",
    "Residual Risk Level",
    "Acceptable",
]


def csv_row_for_rsk(ctx: BuildContext, r: Item) -> list[str]:
    controls = ctx.controls_for(r.id)
    return [
        r.id,
        str(r.get("risk_category") or ""),
        str(r.get("software_function") or ""),
        str(r.get("software_item") or ""),
        str(r.get("hazard") or ""),
        str(r.get("initiating_causes") or "").replace("\n", " | "),
        str(r.get("foreseeable_sequence") or "").replace("\n", " | "),
        str(r.get("hazardous_situation") or ""),
        str(r.get("harm") or ""),
        str(r.get("severity") or ""),
        str(r.get("probability") or ""),
        str(r.get("risk_level") or ""),
        str(r.get("control_hierarchy") or ""),
        ";".join(c.id for c in controls),
        str(r.get("residual_severity") or ""),
        str(r.get("residual_probability") or ""),
        str(r.get("residual_risk_level") or ""),
        str(r.get("residual_acceptable")),
    ]


def csv_row_for_prsk(ctx: BuildContext, p: Item) -> list[str]:
    controls = ctx.controls_for(p.id)
    return [
        p.id,
        "Production",
        str(p.get("production_phase") or ""),  # reuse "Software Function" column
        str(p.get("asset_at_risk") or ""),     # reuse "Software Item" column
        str(p.get("hazard") or ""),
        str(p.get("initiating_causes") or "").replace("\n", " | "),
        str(p.get("foreseeable_sequence") or "").replace("\n", " | "),
        str(p.get("hazardous_situation") or ""),
        str(p.get("harm") or ""),
        str(p.get("severity") or ""),
        str(p.get("probability") or ""),
        str(p.get("risk_level") or ""),
        str(p.get("control_hierarchy") or ""),
        ";".join(c.id for c in controls),
        str(p.get("residual_severity") or ""),
        str(p.get("residual_probability") or ""),
        str(p.get("residual_risk_level") or ""),
        str(p.get("residual_acceptable")),
    ]


def csv_row_for_thr(_ctx: BuildContext, t: Item) -> list[str]:
    # Compact CIA summary for the "Initial Severity" column (stays within 18-col schema)
    c = t.get("confidentiality_severity") or "n/a"
    i = t.get("integrity_severity") or "n/a"
    a = t.get("availability_severity") or "n/a"
    cia_initial = f"Conf={c}, Integ={i}, Avail={a}"
    rc = t.get("residual_confidentiality_severity") or "n/a"
    ri = t.get("residual_integrity_severity") or "n/a"
    ra = t.get("residual_availability_severity") or "n/a"
    cia_residual = f"Conf={rc}, Integ={ri}, Avail={ra}"
    return [
        t.id, "Cyber", "", "", str(t.get("asset") or ""), "", "",
        "", "", cia_initial, str(t.get("likelihood") or ""),
        str(t.get("risk_level") or ""), "", "", cia_residual, "", "",
        str(t.get("residual_acceptable")),
    ]


def csv_row_for_ursk(_ctx: BuildContext, u: Item) -> list[str]:
    return [
        u.id, "Usability", "", "", str(u.get("hazard") or ""), "",
        str(u.get("use_error") or ""), str(u.get("hazardous_situation") or ""),
        str(u.get("harm") or ""), str(u.get("severity") or ""),
        str(u.get("likelihood") or ""), str(u.get("risk_level") or ""), "", "", "",
        "", "", str(u.get("residual_acceptable")),
    ]


def write_csv(ctx: BuildContext, csv_path: Path) -> int:
    rows = 0
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(CSV_HEADER)
        for r in sorted(ctx.rsk, key=lambda i: i.id):
            if r.status == "Deprecated":
                continue
            w.writerow(csv_row_for_rsk(ctx, r))
            rows += 1
        for p in sorted(ctx.prsk, key=lambda i: i.id):
            if p.status == "Deprecated":
                continue
            w.writerow(csv_row_for_prsk(ctx, p))
            rows += 1
        for t in sorted(ctx.thr, key=lambda i: i.id):
            if t.status == "Deprecated":
                continue
            w.writerow(csv_row_for_thr(ctx, t))
            rows += 1
        for u in sorted(ctx.ursk, key=lambda i: i.id):
            if u.status == "Deprecated":
                continue
            w.writerow(csv_row_for_ursk(ctx, u))
            rows += 1
    return rows


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


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
    parser = argparse.ArgumentParser(description="Build the QMS-ready Risk Analysis Report.")
    parser.add_argument("--strict", action="store_true", help="Exit 1 if [TODO] or unacceptable residual remain.")
    parser.add_argument("--md-only", action="store_true", help="Skip .docx rendering.")
    args = parser.parse_args()

    config: dict = {}
    if CONFIG_PATH.is_file():
        try:
            config = parse_yaml(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"ERROR: failed to parse dt-config.yaml: {e}", file=sys.stderr)
            return 1
    else:
        print("WARN: dt-config.yaml not found — using defaults with [TODO]", file=sys.stderr)

    clinical = load_clinical_context(CLINICAL_PATH)

    rsk = load_items("RSK", ITEMS_DIR)
    if not rsk:
        print("ERROR: no RSK items under docs/items/RSK/. Run /doc-62304 first.", file=sys.stderr)
        return 1
    thr = load_items("THR", ITEMS_DIR)
    ursk = load_items("URSK", ITEMS_DIR)
    prsk = load_items("PRSK", ITEMS_DIR)

    mitigators: list[Item] = []
    for cat in ("SRS", "SDS", "TC"):
        mitigators += load_items(cat, ITEMS_DIR)

    ctx = BuildContext(
        config=config,
        clinical=clinical,
        rsk=rsk,
        thr=thr,
        ursk=ursk,
        prsk=prsk,
        mitigators=mitigators,
    )

    md = render_markdown(ctx)

    doc = (config.get("document") or {}) if config else {}
    identifier = str(doc.get("identifier") or "UNKNOWN").strip()
    version_label = str(doc.get("version_label") or "V01").strip()
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    md_path = EXPORT_DIR / f"{identifier}-{version_label}-RISK-REPORT.md"
    docx_path = EXPORT_DIR / f"{identifier}-{version_label}-RISK-REPORT.docx"
    csv_path = EXPORT_DIR / f"{identifier}-{version_label}-RISK-TABLE.csv"
    log_path = EXPORT_DIR / f"{identifier}-{version_label}-risk-export.log"

    md_path.write_text(md, encoding="utf-8")
    ctx.log(f"OK: wrote {md_path.relative_to(ROOT)} ({md.count(chr(10))} lines)")

    rows = write_csv(ctx, csv_path)
    ctx.log(f"OK: wrote {csv_path.relative_to(ROOT)} ({rows} rows)")

    n_rsk_blocked = sum(
        1 for r in rsk if r.status != "Deprecated" and r.get("residual_acceptable") is False
    )
    n_info_safety = sum(
        1
        for r in rsk
        if r.status != "Deprecated" and r.get("control_hierarchy") == "information_for_safety"
    )
    n_cascade = sum(1 for r in rsk if r.status != "Deprecated" and (r.get("arising_risks") or []))
    n_prsk_blocked = sum(
        1 for p in prsk if p.status != "Deprecated" and p.get("residual_acceptable") is False
    )
    todos = count_todos(md)
    ctx.log(f"Items: {len(rsk)} RSK, {len(prsk)} PRSK, {len(thr)} THR, {len(ursk)} URSK")
    ctx.log(f"RSK residual not acceptable: {n_rsk_blocked}")
    ctx.log(f"PRSK residual not acceptable: {n_prsk_blocked}")
    ctx.log(f"RSK with information_for_safety control: {n_info_safety} (labeling to validate)")
    ctx.log(f"RSK with arising_risks (cascade): {n_cascade}")
    ctx.log(f"TODO markers in deliverable: {len(todos)}")

    if not args.md_only:
        rendering = (config.get("rendering") or {}) if config else {}
        ref = rendering.get("reference_docx")
        ref_path = (ROOT / ref).resolve() if ref else None
        if ref_path or shutil.which("pandoc"):
            try_pandoc(md_path, docx_path, ref_path, ctx)
        else:
            ctx.log("INFO: pandoc unavailable and no reference_docx — skipping .docx")

    header = [
        f"build_risk_export run at {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"identifier={identifier} version_label={version_label}",
        "",
    ]
    log_path.write_text("\n".join(header + ctx.log_lines) + "\n", encoding="utf-8")
    print(str(md_path))

    if args.strict and (todos or n_rsk_blocked or n_prsk_blocked):
        print(
            f"STRICT: {len(todos)} [TODO], {n_rsk_blocked} RSK + {n_prsk_blocked} PRSK not acceptable — failing",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
