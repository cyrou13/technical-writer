#!/usr/bin/env python3
"""Build the IEC 62366-1 Usability deliverable triplet:
   - Usability Engineering File (UEF)
   - Summative Evaluation (USE)
   - UEF Annex 1 — IECEE clause-by-clause compliance checklist

Mirrors the Avicenna AV-DP-CINA-CSP-10-021-UEF / -USE / -Annex1 format.

Reads:
    dt-config.yaml                                (QMS metadata, signatories, refs)
    docs/dt-clinical-context.md                   (narrative sections from QMS)
    docs/items/USC/*.md                           (required — use scenarios)
    docs/items/URSK/*.md                          (optional — use-related risks)
    docs/items/SRS/*.md                           (optional — SRS-USE-MIT-* mitigations)
    docs/items/RSK/*.md                           (optional — safety risks tab "Usability")
    docs/static/sample-size-justification.md      (optional — §5.1 of UEF)
    docs/static/clinical-evidence-questionnaire.md (optional — Annex A of USE)
    docs/static/iec62366-annex1-checklist.csv     (optional — IECEE checklist)

Writes:
    docs/export/<id-uef>-<version>-UEF.md
    docs/export/<id-uef>-<version>-UEF.docx           (if pandoc available)
    docs/export/<id-use>-<version>-USE.md
    docs/export/<id-use>-<version>-USE.docx           (if pandoc available)
    docs/export/<id-annex1>-<version>-UEF-Annex1.md
    docs/export/<id-annex1>-<version>-UEF-Annex1.docx (if pandoc available)
    docs/export/<id-uef>-<version>-use-export.log

Stdlib only. Python 3.12+.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path

# Shared helpers — see tools/_lib.py
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import (  # noqa: E402
    Item,
    load_clinical_context,
    load_items,
    parse_yaml,
    section_with_fallback,
    todo_marker,
)

ROOT = Path.cwd()
CONFIG_PATH = ROOT / "dt-config.yaml"
CLINICAL_PATH = ROOT / "docs" / "dt-clinical-context.md"
ITEMS_DIR = ROOT / "docs" / "items"
EXPORT_DIR = ROOT / "docs" / "export"
STATIC_DIR_LOCAL = ROOT / "docs" / "static"

# Fallback static dir if `docs/static/<file>` is missing in the target repo.
# Resolved at runtime via the CLAUDE_PLUGIN_ROOT env var which is set by the
# Claude Code slash-command runtime; falls back to None when running stand-alone.
_PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT")
STATIC_DIR_PLUGIN = Path(_PLUGIN_ROOT) / "scaffold" / "static" if _PLUGIN_ROOT else None


# ---------------------------------------------------------------------------
# Build context
# ---------------------------------------------------------------------------


@dataclass
class BuildContext:
    config: dict
    clinical: dict[str, str]
    usc: list[Item]
    ursk: list[Item]
    srs: list[Item]
    rsk: list[Item]
    template_mode: str  # "platform-rich" | "clinical-narrow"
    log_lines: list[str] = field(default_factory=list)

    def log(self, msg: str) -> None:
        self.log_lines.append(msg)
        print(msg, file=sys.stderr)

    # Convenience: narrative section with fallback to <mark>[TODO]</mark>.
    def section(self, anchor: str, hint: str) -> str:
        return section_with_fallback(
            self.clinical, anchor, hint, config=self.config, root=ROOT
        )


# ---------------------------------------------------------------------------
# Identifier resolution
# ---------------------------------------------------------------------------


def _strip_suffix(identifier: str) -> str:
    """Strip a trailing -SRS / -SDD / -USE / -UEF / -UEF-Annex1 from an ID."""
    for suffix in ("-UEF-Annex1", "-UEF", "-USE", "-SRS", "-SDD", "-STP", "-STDR", "-STR"):
        if identifier.endswith(suffix):
            return identifier[: -len(suffix)]
    return identifier


def resolve_identifiers(config: dict) -> dict[str, str]:
    """Resolve UEF / USE / Annex1 identifiers + version_label + date.

    Priority for each ID:
        1. usability.document.identifier_{uef,use,annex1}
        2. global document.identifier with suffix substitution
        3. "UNKNOWN"
    """
    doc = (config.get("document") or {}) if config else {}
    use_cfg = (config.get("usability") or {}) if config else {}
    use_doc = (use_cfg.get("document") or {}) if use_cfg else {}

    base = str(doc.get("identifier") or "UNKNOWN").strip()
    base_stem = _strip_suffix(base)

    out = {
        "uef": str(use_doc.get("identifier_uef") or f"{base_stem}-UEF").strip(),
        "use": str(use_doc.get("identifier_use") or f"{base_stem}-USE").strip(),
        "annex1": str(use_doc.get("identifier_annex1") or f"{base_stem}-UEF-Annex1").strip(),
        "version_label": str(use_doc.get("version_label") or doc.get("version_label") or "V01").strip(),
        "date": str(use_doc.get("date") or doc.get("date") or "[TODO usability.document.date]").strip(),
    }
    return out


# ---------------------------------------------------------------------------
# Static boilerplate loading
# ---------------------------------------------------------------------------


def load_static(filename: str, ctx: BuildContext) -> str | None:
    """Load a boilerplate file from docs/static/, falling back to plugin scaffold.

    Returns None if neither location has the file (caller substitutes a TODO).
    """
    local = STATIC_DIR_LOCAL / filename
    if local.is_file():
        return local.read_text(encoding="utf-8")
    if STATIC_DIR_PLUGIN is not None:
        plugin_path = STATIC_DIR_PLUGIN / filename
        if plugin_path.is_file():
            ctx.log(
                f"INFO: using plugin-bundled static '{filename}' "
                f"(consider running /doc-init --update to copy it locally)"
            )
            return plugin_path.read_text(encoding="utf-8")
    ctx.log(f"WARN: static boilerplate '{filename}' not found locally or in plugin")
    return None


def _strip_html_comments(md: str) -> str:
    """Remove the leading <!-- ... --> author guidance from a boilerplate file."""
    return re.sub(r"<!--.*?-->", "", md, count=1, flags=re.DOTALL).lstrip()


# ---------------------------------------------------------------------------
# Cover / signatures / revision history — shared across UEF and USE
# ---------------------------------------------------------------------------


def fmt_signatory(ctx: BuildContext, role: str) -> str:
    approvals = (ctx.config.get("approvals") or {}) if ctx.config else {}
    entry = approvals.get(role) or {}
    name = entry.get("name") or "[TODO]"
    job = entry.get("role") or "[TODO]"
    return f"{name} — {job}"


def build_cover(
    ctx: BuildContext, *, title: str, identifier: str, version_label: str, date: str
) -> list[str]:
    return [
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


def build_intro_block(
    ctx: BuildContext, *, document_kind: str, abbreviations_section_id: str = "1.2.1"
) -> list[str]:
    """Build §1 Introduction (overview + abbreviations + glossary + references + conventions).

    Shared between UEF and USE — they differ only in §1.1 wording.
    """
    refs = ctx.config.get("project_references") or [] if ctx.config else []
    id_fmt = (ctx.config.get("id_format") or {}) if ctx.config else {}
    default_fmt = id_fmt.get("default") if isinstance(id_fmt, dict) else None
    if not default_fmt:
        default_fmt = "{CAT}-{DOMAIN}-{NNN:03d}"

    overview_hint = (
        f"One short paragraph describing what THIS {document_kind} covers: "
        f"the device, the lifecycle phase, the scope, and cross-references "
        f"to the Master Plan and downstream test/risk documents."
    )

    lines: list[str] = [
        "# 1. Introduction",
        "",
        "## 1.1 Document overview",
        "",
        ctx.section("document-overview", overview_hint),
        "",
        "## 1.2 Abbreviations and Glossary",
        "",
        f"### {abbreviations_section_id} Abbreviations",
        "",
        ctx.section("abbreviations", "Markdown table or bullet list of abbreviations used."),
        "",
        f"### 1.2.2 Glossary",
        "",
        ctx.section("glossary", "Definitions of domain-specific terms used in this document."),
        "",
        "## 1.3 References",
        "",
        "### 1.3.1 Project references",
        "",
    ]
    if refs:
        lines += ["| # | Document identifier | Document title |", "|---|---|---|"]
        for r in refs:
            if not isinstance(r, dict):
                continue
            label = f"[{r.get('id') or 'R?'}]"
            lines.append(
                f"| {label} | {r.get('identifier') or '[TODO]'} | {r.get('title') or '[TODO]'} |"
            )
    else:
        lines.append("_(no project references configured — edit `dt-config.yaml`)_")
    lines += [
        "",
        "### 1.3.2 Standard and Regulatory references",
        "",
        "| # | Reference | Title |",
        "|---|---|---|",
        "| [STD1] | IEC 62366-1:2015/A1:2020 | Medical devices — Application of usability engineering to medical devices |",
        "| [STD2] | IEC 62366-2:2016 | Medical devices — Part 2: Guidance on the application of usability engineering to medical devices |",
        "| [STD3] | ISO 14971:2019 | Medical devices — Application of risk management to medical devices |",
        "",
        "## 1.4 Conventions",
        "",
        "Items referenced in this document follow the format:",
        "",
        "```",
        default_fmt,
        "```",
        "",
        "where `{CAT}` is the category prefix (USC, URSK, SRS, RSK, …), "
        "`{SUITE}` and `{APP}` come from `dt-config.yaml: product`, "
        "`{DOMAIN}` is a short uppercase identifier per functional area, "
        "and `{NNN}` is a zero-padded counter.",
        "",
        "---",
        "",
    ]
    return lines


# ---------------------------------------------------------------------------
# UEF §2 Use Specification — uses 5 narrative anchors from clinical context
# ---------------------------------------------------------------------------


def build_uef_use_specification(ctx: BuildContext) -> list[str]:
    return [
        "# 2. Use Specification",
        "",
        "Many parts of this document have links to other project documents, which, "
        "for part of them, deal with usability and safety issues. The project "
        "references table in §1.3.1 lists such other documents.",
        "",
        "## 2.1 Intended use",
        "",
        ctx.section(
            "intended-use",
            "Verbatim Intended Use statement from the QMS — must match the labeling and the regulatory submission word-for-word.",
        ),
        "",
        "## 2.2 Equipment application specification",
        "",
        "### 2.2.1 Medical purpose",
        "",
        ctx.section(
            "medical-purpose",
            "IEC 62366-1 §5.1(a) — one paragraph stating the clinical workflow goal of the device.",
        ),
        "",
        "### 2.2.2 Patient population",
        "",
        ctx.section(
            "patient-population",
            "IEC 62366-1 §5.1(b) — the intended patient population (age, weight, exclusions). State 'not applicable' for pure-platform software.",
        ),
        "",
        "### 2.2.3 Intended user",
        "",
        ctx.section(
            "end-users",
            "IEC 62366-1 §5.1(d) — the user profile(s), required training, and supplied documentation.",
        ),
        "",
        "### 2.2.4 Application — use environment",
        "",
        ctx.section(
            "application-environment",
            "IEC 62366-1 §5.1(e) — general/visibility/physical conditions, frequency of use, mobility.",
        ),
        "",
        "### 2.2.5 Resource requirements",
        "",
        ctx.section(
            "resource-requirements",
            "Minimum hardware/software/network configuration required to operate the device safely.",
        ),
        "",
        "---",
        "",
    ]


# ---------------------------------------------------------------------------
# UEF §3 Risk Assessment — DIFFERENT per template mode
# ---------------------------------------------------------------------------


def build_uef_risk_assessment(ctx: BuildContext) -> list[str]:
    """Dispatch to the platform-rich or clinical-narrow §3 builder."""
    if ctx.template_mode == "clinical-narrow":
        return _build_risk_assessment_narrow(ctx)
    return _build_risk_assessment_platform(ctx)


def _escape_cell(s: str) -> str:
    """Escape pipe characters and newlines for a Markdown table cell."""
    return (s or "").replace("\n", " ").replace("|", "\\|").strip()


def _usc_steps(usc: Item) -> list[str]:
    """Extract numbered/bulleted steps under '## Normal usage sequence' in a USC body."""
    body = usc.body
    m = re.search(
        r"^##\s*Normal usage sequence\s*$(.*?)(?=^##\s|\Z)",
        body,
        flags=re.MULTILINE | re.DOTALL,
    )
    if not m:
        return []
    block = m.group(1).strip()
    steps: list[str] = []
    for line in block.splitlines():
        s = line.strip()
        if not s:
            continue
        # Strip leading "1." / "1)" / "-" / "*" markers
        s = re.sub(r"^(\d+[.)]|[-*])\s+", "", s)
        if s:
            steps.append(s)
    return steps


def _build_risk_assessment_platform(ctx: BuildContext) -> list[str]:
    """Platform-rich §3 — tabular, grouped by persona / source surface."""
    active_usc = [u for u in ctx.usc if u.status != "Deprecated"]
    active_ursk = [u for u in ctx.ursk if u.status != "Deprecated"]

    # §3.1.1 — group USC by persona
    by_persona: dict[str, list[Item]] = defaultdict(list)
    for u in active_usc:
        persona = str(u.fm.get("persona") or "[TODO persona]").strip()
        by_persona[persona].append(u)
    for k in by_persona:
        by_persona[k].sort(key=lambda i: i.id)

    # §3.1.2 — group URSK by source surface (first path in `source`)
    def _first_source(it: Item) -> str:
        s = it.fm.get("source")
        if isinstance(s, list) and s:
            return str(s[0])
        if isinstance(s, str) and s.strip():
            return s
        return "[TODO source]"

    by_surface: dict[str, list[Item]] = defaultdict(list)
    for u in active_ursk:
        by_surface[_first_source(u)].append(u)
    for k in by_surface:
        by_surface[k].sort(key=lambda i: i.id)

    # §3.4 — for each URSK, find SRS items where links.mitigates includes the URSK id
    srs_by_mitigates: dict[str, list[Item]] = defaultdict(list)
    for s in ctx.srs:
        if s.status == "Deprecated":
            continue
        for m in s.mitigates:
            srs_by_mitigates[m].append(s)

    lines: list[str] = ["# 3. Risk assessment", ""]

    # ----- §3.1 Characteristics related to safety -----
    lines += [
        "## 3.1 Characteristics related to safety",
        "",
        "### 3.1.1 Primary operating functions and use scenarios",
        "",
        "The table below lists the primary operating functions of the device, grouped "
        "by user persona. Each entry references the underlying use scenario item(s) "
        "(USC) that capture the detailed steps. The full body of each USC is the "
        "authoritative source — this table is the index.",
        "",
        "| Persona | Use scenario | USC ID | Linked safety items |",
        "|---|---|---|---|",
    ]
    if active_usc:
        for persona in sorted(by_persona):
            for u in by_persona[persona]:
                parents = ", ".join(u.parents) if u.parents else "—"
                lines.append(
                    f"| {_escape_cell(persona)} "
                    f"| {_escape_cell(u.title)} "
                    f"| {u.id} "
                    f"| {_escape_cell(parents)} |"
                )
    else:
        lines.append("| [TODO persona] | [TODO scenario] | — | — |")
    lines += ["", ""]

    # ----- §3.1.2 Reasonably foreseeable use errors -----
    lines += [
        "### 3.1.2 Reasonably foreseeable use errors",
        "",
        "The table below enumerates the reasonably foreseeable use errors identified "
        "during the analysis of each user interface surface. Each error is captured "
        "as a URSK (Use-related Risk) item where the full causal chain "
        "(use error → hazard → harm) is documented.",
        "",
        "| UI surface | Use error | URSK ID | Parent USC |",
        "|---|---|---|---|",
    ]
    if active_ursk:
        for surface in sorted(by_surface):
            for u in by_surface[surface]:
                use_error = str(u.fm.get("use_error") or "[TODO use_error]")
                parent_usc = str(u.fm.get("use_scenario") or "—")
                lines.append(
                    f"| {_escape_cell(surface)} "
                    f"| {_escape_cell(use_error)} "
                    f"| {u.id} "
                    f"| {parent_usc} |"
                )
    else:
        lines.append("| [TODO surface] | [TODO use error] | — | — |")
    lines += ["", ""]

    # ----- §3.2 Hazardous situations -----
    lines += [
        "## 3.2 Hazardous situations and hazard-related use scenarios",
        "",
        "The table below lists the hazardous situations resulting from the foreseeable "
        "use errors of §3.1.2, with their severity, likelihood and pre-mitigation risk "
        "level per ISO 14971. Items with `risk_level = Low` are kept in the underlying "
        "URSK files but excluded from this summary; the complete inventory is available "
        "in the Risk Analysis spreadsheet (sheet \"Usability\").",
        "",
        "| URSK ID | Hazardous situation | Harm | Severity | Likelihood | Risk level |",
        "|---|---|---|---|---|---|",
    ]
    relevant = [u for u in active_ursk if str(u.fm.get("risk_level") or "Low") != "Low"]
    if relevant:
        for u in sorted(relevant, key=lambda i: i.id):
            lines.append(
                f"| {u.id} "
                f"| {_escape_cell(str(u.fm.get('hazardous_situation') or '[TODO]'))} "
                f"| {_escape_cell(str(u.fm.get('harm') or '[TODO]'))} "
                f"| {u.fm.get('severity') or '—'} "
                f"| {u.fm.get('likelihood') or '—'} "
                f"| {u.fm.get('risk_level') or '—'} |"
            )
    else:
        if active_ursk:
            lines.append(
                f"| _(no URSK with risk_level > Low — full inventory in Risk Analysis spreadsheet)_ "
                f"| — | — | — | — | — |"
            )
        else:
            lines.append("| [TODO] | [TODO] | [TODO] | — | — | — |")
    lines += ["", ""]

    # ----- §3.3 Hazard-related use scenarios for summative evaluation -----
    summative = [u for u in active_ursk if bool(u.fm.get("summative"))]
    lines += [
        "## 3.3 Hazard-related use scenarios for summative evaluation",
        "",
    ]
    if summative:
        lines += [
            "The hazard-related use scenarios listed below have been selected for "
            "inclusion in the summative evaluation protocol. The selection is based "
            "on each URSK's pre-mitigation risk level and the criticality of the "
            "underlying use scenario.",
            "",
            "| URSK ID | Hazardous situation | Pre-mitigation risk |",
            "|---|---|---|",
        ]
        for u in sorted(summative, key=lambda i: i.id):
            lines.append(
                f"| {u.id} "
                f"| {_escape_cell(str(u.fm.get('hazardous_situation') or '[TODO]'))} "
                f"| {u.fm.get('risk_level') or '—'} |"
            )
    else:
        lines.append(
            todo_marker(
                "summative-selection-rationale",
                "Select the hazard-related use scenarios to include in the summative "
                "evaluation. Either set `summative: true` on the relevant URSK items, "
                "or document here why all URSKs are included (e.g. \"limited user "
                "interaction, all hazard-related scenarios retained\").",
            )
        )
    lines += ["", ""]

    # ----- §3.4 Mitigation actions and the user interface specification -----
    lines += [
        "## 3.4 Mitigation actions and the user interface specification",
        "",
        "Mitigation actions follow the IEC 62366-1 §4.1.2 / ISO 14971 §7.1 hierarchy "
        "(inherent safety by design **D** > protective measures **P** > information for "
        "safety **I**). The user interface specification is documented in the Software "
        "Requirements Specification — the table below links each URSK to its mitigating "
        "SRS items.",
        "",
        "| URSK ID | Use error | Mitigating SRS | Verifying TC |",
        "|---|---|---|---|",
    ]
    # Build TC verification map: for each SRS, list TC IDs whose links.verifies includes it
    tc_by_srs: dict[str, list[str]] = defaultdict(list)
    for tc in load_items("TC", ITEMS_DIR):
        verifies = (tc.fm.get("links") or {}).get("verifies") or []
        for sid in verifies:
            tc_by_srs[sid].append(tc.id)

    if active_ursk:
        for u in sorted(active_ursk, key=lambda i: i.id):
            mitigations = srs_by_mitigates.get(u.id, [])
            if mitigations:
                srs_ids = ", ".join(s.id for s in mitigations)
                tcs: list[str] = []
                for s in mitigations:
                    tcs += tc_by_srs.get(s.id, [])
                tcs_str = ", ".join(sorted(set(tcs))) if tcs else "[TODO TC]"
            else:
                srs_ids = "[GAP-MIT no SRS mitigates this URSK]"
                tcs_str = "—"
            lines.append(
                f"| {u.id} "
                f"| {_escape_cell(str(u.fm.get('use_error') or '[TODO]'))} "
                f"| {_escape_cell(srs_ids)} "
                f"| {_escape_cell(tcs_str)} |"
            )
    else:
        lines.append("| — | — | — | — |")
    lines += ["", "---", ""]
    return lines


def _build_risk_assessment_narrow(ctx: BuildContext) -> list[str]:
    """Clinical-narrow §3 — narrative 6-step linear scenario (CSpine-style)."""
    active_usc = [u for u in ctx.usc if u.status != "Deprecated"]
    active_ursk = [u for u in ctx.ursk if u.status != "Deprecated"]
    lines: list[str] = [
        "# 3. Risk assessment",
        "",
        "## 3.1 Characteristics related to safety",
        "",
        "### 3.1.1 Primary operating functions and use scenarios",
        "",
        "The user interaction with the device is limited. The correct use scenario "
        "is detailed below.",
        "",
        "**Use Scenario steps:**",
        "",
    ]
    if not active_usc:
        lines.append("[TODO populate USC items under docs/items/USC/]")
    else:
        # Flatten the steps from all USCs in order
        letters = "abcdefghijklmnopqrstuvwxyz"
        idx = 0
        for u in active_usc:
            steps = _usc_steps(u)
            for step in steps:
                if idx >= len(letters):
                    break
                lines.append(f"{letters[idx]}. {step}")
                idx += 1
    lines += [
        "",
        "### 3.1.2 Reasonably foreseeable use errors",
        "",
        "The aforementioned use scenario is input data for the device risk analysis "
        "related to the use of the software by the intended user. The worst-case "
        "scenarios are detailed below:",
        "",
    ]
    if active_ursk:
        for u in active_ursk:
            lines.append(
                f"- **{u.id}** — {_escape_cell(str(u.fm.get('use_error') or '[TODO]'))}: "
                f"{_escape_cell(str(u.fm.get('hazardous_situation') or '[TODO]'))}"
            )
    else:
        lines.append("- [TODO populate URSK items under docs/items/URSK/]")
    lines += [
        "",
        "## 3.2 Hazardous situations and hazard-related use scenarios",
        "",
        "Hazardous situations and hazard-related use scenarios are described in the "
        "device Risk analysis and traceability Table, \"Usability\" tab.",
        "",
        "## 3.3 Hazard-related use scenarios for summative evaluation",
        "",
        "Knowing that the user interaction with the device is limited, it has been "
        "decided to select all the hazard-related use scenarios described in the "
        "Risk analysis and traceability Table, \"Usability\" tab, for the summative "
        "evaluation independently of any criteria based on their severity or "
        "probability before risk mitigation.",
        "",
        "## 3.4 Mitigation actions and the user interface specification",
        "",
        "Mitigation actions are documented in the Risk Analysis and Traceability Table. "
        "They may include in the following order of priority: 1) inherent safety by "
        "design (D), 2) protective measures in the medical device itself or in the "
        "production process (P), 3) information for safety (I). A traceability with "
        "the software requirement specification is also provided. User interface "
        "specification is documented in the software requirement specification "
        "document.",
        "",
        "---",
        "",
    ]
    return lines


def build_uef_formative(ctx: BuildContext) -> list[str]:
    return [
        "# 4. Formative Evaluations",
        "",
        todo_marker(
            "formative-history",
            "Narrative log of pre-summative user studies, beta program sessions, "
            "design review meetings. List participants (name, MD, affiliation, date), "
            "scope of each session, and design decisions taken as a result. By essence "
            "QMS-side — not derivable from code.",
        ),
        "",
        "---",
        "",
    ]


def build_uef_summative(ctx: BuildContext, identifiers: dict[str, str]) -> list[str]:
    """§5 Summative Evaluations — §5.1 boilerplate, §5.2/5.3 cross-ref to USE."""
    boilerplate = load_static("sample-size-justification.md", ctx)
    if boilerplate is None:
        sample_block = todo_marker(
            "sample-size-justification",
            "Sample size justification missing — populate docs/static/sample-size-justification.md "
            "or run /doc-init --update to scaffold the default boilerplate.",
        )
    else:
        sample_block = _strip_html_comments(boilerplate).strip()

    use_ref = identifiers["use"]
    use_ver = identifiers["version_label"]

    return [
        "# 5. Summative Evaluations",
        "",
        "## 5.1 Sample size for usability testing",
        "",
        sample_block,
        "",
        "## 5.2 Summative Evaluation Protocol",
        "",
        f"The detailed summative evaluation protocol is recorded in the "
        f"Usability Summative Evaluation document (**{use_ref}-{use_ver}**), §2.",
        "",
        "## 5.3 Summative Evaluation Report",
        "",
        f"The summative evaluation report is recorded in the Usability Summative "
        f"Evaluation document (**{use_ref}-{use_ver}**), §3.",
        "",
    ]


# ---------------------------------------------------------------------------
# USE — Summative Evaluation document
# ---------------------------------------------------------------------------


def _resolve_contact(ctx: BuildContext) -> dict[str, str]:
    """Resolve contact fields for the Annex A questionnaire.

    Priority:
        1. usability.contact.{name,role,email}
        2. approvals.written_by.{name,role}
        3. [TODO]
    """
    use_cfg = (ctx.config.get("usability") or {}) if ctx.config else {}
    contact = (use_cfg.get("contact") or {}) if use_cfg else {}
    approvals = (ctx.config.get("approvals") or {}) if ctx.config else {}
    written = (approvals.get("written_by") or {}) if approvals else {}
    return {
        "name": str(contact.get("name") or written.get("name") or "[TODO contact.name]"),
        "role": str(contact.get("role") or written.get("role") or "[TODO contact.role]"),
        "email": str(contact.get("email") or "[TODO contact.email]"),
    }


def build_use_document(
    ctx: BuildContext, identifiers: dict[str, str], doc_title: str
) -> list[str]:
    """USE — Usability Summative Evaluation document.

    Structure: §1 Intro → §2 Protocol (auto from USC) → §3 Report (TODO) → Annex A questionnaire.
    """
    active_usc = [u for u in ctx.usc if u.status != "Deprecated"]

    lines: list[str] = []
    lines += build_intro_block(ctx, document_kind="Usability Summative Evaluation")

    # §2 Summative Evaluation Protocol
    lines += [
        "# 2. Summative Evaluation Protocol",
        "",
        "## 2.1 Conditions of tests",
        "",
        todo_marker(
            "test-conditions",
            "Document the conditions of the summative test: user profile and "
            "affiliation, training level, test environment (clinical / near-clinical / "
            "remote), hardware and software setup, network configuration, data sources, "
            "duration, observer setup, recording strategy. Reference §2.2 of IEC 62366-1.",
        ),
        "",
        "## 2.2 Test scenarios",
        "",
        "The following general test scenarios, describing users' actions related to "
        "primary operating functions of the device, shall be performed by each test "
        "participant:",
        "",
    ]
    if active_usc:
        # High-level enumeration: one bullet per USC
        for k, u in enumerate(active_usc, 1):
            persona = u.fm.get("persona") or "—"
            lines.append(f"{k}. **{u.title}** _(persona: {persona}, ref: {u.id})_")
        lines += ["", "**Detailed test scenario steps:**", ""]
        for u in active_usc:
            lines.append(f"**{u.id} — {u.title}**")
            lines.append("")
            steps = _usc_steps(u)
            if steps:
                for k, step in enumerate(steps, 1):
                    lines.append(f"{k}. {step}")
            else:
                lines.append("[TODO populate the `## Normal usage sequence` section of this USC]")
            lines.append("")
    else:
        lines.append("[TODO no USC items found — populate docs/items/USC/]")
        lines.append("")

    lines += [
        "## 2.3 Evaluation form",
        "",
        "The evaluation form to be filled by each user participating in the test is "
        "presented within **Annex A** of this document.",
        "",
        "## 2.4 Evaluation criteria",
        "",
        todo_marker(
            "summative-criteria",
            "State the pass criterion for the summative evaluation. Example: \"The "
            "expected success rate is that all N users answer YES to all the usability "
            "tests listed in the evaluation form in Annex A\". If the device has "
            "performance-related criteria (latency, accuracy), state them as well.",
        ),
        "",
        "---",
        "",
    ]

    # §3 Summative Evaluation Report
    lines += [
        "# 3. Summative Evaluation Report",
        "",
        "## 3.1 Overview of summative evaluation",
        "",
        todo_marker(
            "summative-overview",
            "Document the overview of the summative evaluation: participants (name, "
            "MD, affiliation, expertise level), period of the evaluation, used material, "
            "tested data description, and the impact of the test environment on the "
            "results. This section is filled in AFTER the test sessions are conducted.",
        ),
        "",
        "## 3.2 Test results",
        "",
        todo_marker(
            "summative-results",
            "Document the test results: summary table per scenario × participant "
            "(pass/fail), narrative description of any blocking bug or issue, processing "
            "time observations, free-text feedback. Indicate whether any new hazard-"
            "related use scenario was discovered during testing.",
        ),
        "",
        "## 3.3 Conclusion",
        "",
        todo_marker(
            "summative-conclusion",
            "State the conclusion: whether the summative evaluation passed against "
            "the §2.4 criteria, whether the usability of the user interface is "
            "validated, and any follow-up actions if not.",
        ),
        "",
        "---",
        "",
    ]

    # Annex A — questionnaire
    boilerplate = load_static("clinical-evidence-questionnaire.md", ctx)
    if boilerplate is None:
        annex = todo_marker(
            "clinical-evidence-questionnaire",
            "Annex A questionnaire boilerplate is missing — populate "
            "docs/static/clinical-evidence-questionnaire.md or run /doc-init --update.",
        )
    else:
        annex = _strip_html_comments(boilerplate).strip()
        # Substitute placeholders
        contact = _resolve_contact(ctx)
        doc = (ctx.config.get("document") or {}) if ctx.config else {}
        device_name = str(doc.get("short_name") or doc.get("title") or "[TODO device-name]")
        device_version = str(doc.get("version_label") or "[TODO device-version]")
        annex = (
            annex
            .replace("{DEVICE_NAME}", device_name)
            .replace("{DEVICE_VERSION}", device_version)
            .replace("{CONTACT_NAME}", contact["name"])
            .replace("{CONTACT_ROLE}", contact["role"])
            .replace("{CONTACT_EMAIL}", contact["email"])
        )

    lines += [
        "# Annex A — Clinical Evidence Questionnaire (Summative Evaluation)",
        "",
        annex,
        "",
    ]
    return lines


# ---------------------------------------------------------------------------
# UEF Annex 1 — IECEE clause checklist
# ---------------------------------------------------------------------------


def _resolve_risk_report_ref(ctx: BuildContext) -> str:
    """Resolve the Risk Report cross-reference for Annex 1 clauses 4.1.2 / 5.3 / 5.4."""
    use_cfg = (ctx.config.get("usability") or {}) if ctx.config else {}
    explicit = use_cfg.get("risk_report_ref")
    if explicit:
        return str(explicit)
    # Fallback: scan project_references for an item whose title or identifier
    # looks like a risk report / risk analysis document.
    refs = ctx.config.get("project_references") or [] if ctx.config else []
    for r in refs:
        if not isinstance(r, dict):
            continue
        haystack = f"{r.get('identifier') or ''} {r.get('title') or ''}".lower()
        if "risk" in haystack and ("analysis" in haystack or "report" in haystack or "ras" in haystack):
            return f"{r.get('identifier') or '[TODO]'}"
    return "[TODO risk-report-ref — set usability.risk_report_ref in dt-config.yaml]"


def _load_checklist(ctx: BuildContext) -> list[dict[str, str]]:
    """Load the IECEE clause checklist CSV. Returns [] if missing."""
    raw = load_static("iec62366-annex1-checklist.csv", ctx)
    if raw is None:
        return []
    rows: list[dict[str, str]] = []
    reader = csv.DictReader(StringIO(raw))
    for row in reader:
        rows.append({k: (v or "").strip() for k, v in row.items()})
    return rows


def build_uef_annex1(
    ctx: BuildContext, identifiers: dict[str, str], doc_title: str
) -> list[str]:
    """UEF Annex 1 — IECEE clause-by-clause compliance checklist."""
    doc = (ctx.config.get("document") or {}) if ctx.config else {}
    org = str(doc.get("manufacturer") or doc.get("short_name") or "[TODO manufacturer]")
    risk_report_ref = _resolve_risk_report_ref(ctx)
    srs_ref = _strip_suffix(str(doc.get("identifier") or "UNKNOWN")) + "-SRS"

    placeholders = {
        "{UEF_REF}": f"{identifiers['uef']}-{identifiers['version_label']}",
        "{USE_REF}": f"{identifiers['use']}-{identifiers['version_label']}",
        "{SRS_REF}": srs_ref,
        "{RISK_REPORT_REF}": risk_report_ref,
    }

    def _subst(s: str) -> str:
        for k, v in placeholders.items():
            s = s.replace(k, v)
        return s

    lines: list[str] = []

    # ----- Identification table -----
    lines += [
        "## Identification",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Standard | IEC 62366-1:2015/A1:2020 — Medical devices, Part 1: Application of usability engineering to medical devices |",
        f"| Report reference No. | {identifiers['annex1']}-{identifiers['version_label']} |",
        f"| Compiled by | {fmt_signatory(ctx, 'written_by')} |",
        f"| Approved by | {fmt_signatory(ctx, 'approved_by')} |",
        f"| Date of issue | {identifiers['date']} |",
        f"| Manufacturer | {org} |",
        f"| Device under evaluation | {doc.get('title') or '[TODO device]'} |",
        f"| Linked Usability Engineering File | {identifiers['uef']}-{identifiers['version_label']} |",
        f"| Linked Summative Evaluation | {identifiers['use']}-{identifiers['version_label']} |",
        f"| Linked Risk Analysis | {risk_report_ref} |",
        "",
        "**Verdict legend:** P = Pass · F = Fail · NA = Not Applicable.",
        "",
        "---",
        "",
    ]

    # ----- Load and render clause tables -----
    rows = _load_checklist(ctx)
    if not rows:
        lines += [
            todo_marker(
                "iec62366-annex1-checklist",
                "Clause checklist boilerplate is missing — populate "
                "docs/static/iec62366-annex1-checklist.csv or run /doc-init --update.",
            ),
            "",
        ]
        return lines

    # Partition by leading clause section: "4" → Table 2, "5" → Table 3.
    def _section(clause: str) -> str:
        if not clause:
            return "?"
        return clause.split(".")[0]

    by_section: dict[str, list[dict[str, str]]] = defaultdict(list)
    for r in rows:
        by_section[_section(r.get("clause", ""))].append(r)

    section_titles = {
        "4": "Clause 4 — Principles (General requirements)",
        "5": "Clause 5 — Usability Engineering Process",
    }
    table_index = 2  # Identification was Table 1
    for sec in ("4", "5"):
        srows = by_section.get(sec, [])
        if not srows:
            continue
        lines += [
            f"## Table {table_index} — {section_titles.get(sec, f'Clause {sec}')}",
            "",
            "| Clause | Requirement | Result / Remark | Verdict |",
            "|---|---|---|---|",
        ]
        for r in srows:
            clause = r.get("clause", "—")
            requirement = _subst(r.get("requirement", "—"))
            result = _subst(r.get("result_pointer", "—"))
            verdict = r.get("verdict", "—") or "—"
            lines.append(
                f"| {_escape_cell(clause)} "
                f"| {_escape_cell(requirement)} "
                f"| {_escape_cell(result)} "
                f"| {_escape_cell(verdict)} |"
            )
        lines += ["", ""]
        table_index += 1

    lines += ["---", ""]
    return lines


# ---------------------------------------------------------------------------
# Pandoc rendering
# ---------------------------------------------------------------------------


def try_pandoc(
    md_path: Path, docx_path: Path, reference_docx: Path | None, ctx: BuildContext
) -> bool:
    pandoc = shutil.which("pandoc")
    if not pandoc:
        ctx.log(f"INFO: pandoc not found — .docx not produced for {md_path.name}")
        return False
    cmd = [pandoc, str(md_path), "--toc", "--toc-depth=3", "-o", str(docx_path)]
    if reference_docx and reference_docx.is_file():
        cmd.insert(2, f"--reference-doc={reference_docx}")
    elif reference_docx:
        ctx.log(
            f"WARN: reference_docx '{reference_docx}' not found — using pandoc default style"
        )
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        ctx.log(f"WARN: pandoc failed for {md_path.name} (rc={proc.returncode}): "
                f"{proc.stderr.strip()[:300]}")
        return False
    ctx.log(f"OK: wrote {docx_path.relative_to(ROOT)}")
    return True


def count_todos(md: str) -> list[str]:
    return re.findall(r"\[TODO[^\]]*\]", md)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def render_uef(ctx: BuildContext, identifiers: dict[str, str], doc_title: str) -> str:
    parts: list[str] = []
    parts += build_cover(
        ctx,
        title=doc_title,
        identifier=identifiers["uef"],
        version_label=identifiers["version_label"],
        date=identifiers["date"],
    )
    parts += build_revision_history(ctx)
    parts += build_intro_block(ctx, document_kind="Usability Engineering File")
    parts += build_uef_use_specification(ctx)
    parts += build_uef_risk_assessment(ctx)
    parts += build_uef_formative(ctx)
    parts += build_uef_summative(ctx, identifiers)
    return "\n".join(parts).rstrip() + "\n"


def render_use(ctx: BuildContext, identifiers: dict[str, str], doc_title: str) -> str:
    parts: list[str] = []
    parts += build_cover(
        ctx,
        title=doc_title,
        identifier=identifiers["use"],
        version_label=identifiers["version_label"],
        date=identifiers["date"],
    )
    parts += build_revision_history(ctx)
    parts += build_use_document(ctx, identifiers, doc_title)
    return "\n".join(parts).rstrip() + "\n"


def render_annex1(ctx: BuildContext, identifiers: dict[str, str], doc_title: str) -> str:
    parts: list[str] = []
    parts += build_cover(
        ctx,
        title=doc_title,
        identifier=identifiers["annex1"],
        version_label=identifiers["version_label"],
        date=identifiers["date"],
    )
    parts += build_uef_annex1(ctx, identifiers, doc_title)
    return "\n".join(parts).rstrip() + "\n"


def derive_doc_titles(config: dict) -> dict[str, str]:
    """Derive UEF / USE / Annex1 document titles from `document.title` if set."""
    doc = (config.get("document") or {}) if config else {}
    base = str(doc.get("title") or "[TODO document.title]").strip()
    # If base contains "Software Requirements Specification" or similar, replace.
    base_clean = re.sub(
        r"\b(Software Requirements Specification|Software Design Description|"
        r"Software Test Plan|Software Test Description)\b",
        "",
        base,
    ).strip(" —-")
    if not base_clean:
        base_clean = base
    return {
        "uef": f"{base_clean} — Usability Engineering File",
        "use": f"{base_clean} — Usability Summative Evaluation",
        "annex1": f"{base_clean} — UEF Annex 1 (IEC 62366-1 Compliance Checklist)",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the IEC 62366-1 Usability deliverable triplet."
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if any deliverable contains [TODO] markers or URSKs without mitigation.",
    )
    parser.add_argument(
        "--md-only",
        action="store_true",
        help="Skip .docx rendering even if pandoc is available.",
    )
    parser.add_argument(
        "--template",
        choices=["platform-rich", "clinical-narrow"],
        help="Override usability.template from dt-config.yaml for this run.",
    )
    parser.add_argument(
        "--only",
        choices=["uef", "use", "annex1"],
        help="Generate only one of the three deliverables.",
    )
    args = parser.parse_args()

    # Config
    config: dict = {}
    if CONFIG_PATH.is_file():
        try:
            config = parse_yaml(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"ERROR: failed to parse dt-config.yaml: {e}", file=sys.stderr)
            return 1
    else:
        print(
            "WARN: dt-config.yaml not found — using defaults with [TODO] placeholders",
            file=sys.stderr,
        )

    # Clinical context
    clinical = load_clinical_context(CLINICAL_PATH)
    if not CLINICAL_PATH.is_file():
        print(
            "WARN: docs/dt-clinical-context.md not found — narrative sections will be [TODO]",
            file=sys.stderr,
        )

    # Items
    usc = load_items("USC", ITEMS_DIR)
    ursk = load_items("URSK", ITEMS_DIR)
    srs = load_items("SRS", ITEMS_DIR)
    rsk = load_items("RSK", ITEMS_DIR)
    if not usc:
        print(
            "ERROR: no USC items found under docs/items/USC/. Run /doc-62304 first.",
            file=sys.stderr,
        )
        return 1

    # Template mode
    use_cfg = (config.get("usability") or {}) if config else {}
    template_mode = args.template or use_cfg.get("template") or "platform-rich"
    if template_mode not in ("platform-rich", "clinical-narrow"):
        print(
            f"WARN: unknown usability.template '{template_mode}' — falling back to platform-rich",
            file=sys.stderr,
        )
        template_mode = "platform-rich"

    ctx = BuildContext(
        config=config,
        clinical=clinical,
        usc=usc,
        ursk=ursk,
        srs=srs,
        rsk=rsk,
        template_mode=template_mode,
    )

    # Auto-suggestion if the chosen mode looks wrong
    personas = {(u.fm.get("persona") or "").strip() for u in usc if u.fm.get("persona")}
    if template_mode == "platform-rich" and len(usc) <= 10 and len(personas) <= 1:
        ctx.log(
            "INFO: USC count ≤ 10 and ≤ 1 persona — `clinical-narrow` mode might fit better. "
            "Override via `--template clinical-narrow` or `usability.template` in dt-config.yaml."
        )
    ctx.log(
        f"Selected template: `{template_mode}` "
        f"(override via `usability.template` in dt-config.yaml or `--template`)."
    )
    ctx.log(
        f"Items: {len(usc)} USC, {len(ursk)} URSK, {len(srs)} SRS, {len(rsk)} RSK. "
        f"Distinct USC personas: {len(personas)}."
    )

    # Resolve identifiers + titles
    identifiers = resolve_identifiers(config)
    titles = derive_doc_titles(config)

    # Render
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    version_label = identifiers["version_label"]
    rendered: dict[str, tuple[Path, str]] = {}

    if args.only in (None, "uef"):
        md = render_uef(ctx, identifiers, titles["uef"])
        path = EXPORT_DIR / f"{identifiers['uef']}-{version_label}-UEF.md"
        path.write_text(md, encoding="utf-8")
        rendered["uef"] = (path, md)
        ctx.log(f"OK: wrote {path.relative_to(ROOT)} ({md.count(chr(10))} lines)")

    if args.only in (None, "use"):
        md = render_use(ctx, identifiers, titles["use"])
        path = EXPORT_DIR / f"{identifiers['use']}-{version_label}-USE.md"
        path.write_text(md, encoding="utf-8")
        rendered["use"] = (path, md)
        ctx.log(f"OK: wrote {path.relative_to(ROOT)} ({md.count(chr(10))} lines)")

    if args.only in (None, "annex1"):
        md = render_annex1(ctx, identifiers, titles["annex1"])
        path = EXPORT_DIR / f"{identifiers['annex1']}-{version_label}-UEF-Annex1.md"
        path.write_text(md, encoding="utf-8")
        rendered["annex1"] = (path, md)
        ctx.log(f"OK: wrote {path.relative_to(ROOT)} ({md.count(chr(10))} lines)")

    # Pandoc
    if not args.md_only:
        rendering = (config.get("rendering") or {}) if config else {}
        ref = rendering.get("reference_docx")
        ref_path = (ROOT / ref).resolve() if ref else None
        for kind, (md_path, _md) in rendered.items():
            docx_path = md_path.with_suffix(".docx")
            if ref_path or shutil.which("pandoc"):
                try_pandoc(md_path, docx_path, ref_path, ctx)
            else:
                ctx.log(f"INFO: pandoc unavailable and no reference_docx — skipping .docx for {kind}")

    # Stats
    total_todos = 0
    for kind, (_p, md) in rendered.items():
        todos = count_todos(md)
        ctx.log(f"TODO markers in {kind.upper()}: {len(todos)}")
        total_todos += len(todos)

    # URSK without mitigation SRS
    mitigated: set[str] = set()
    for s in srs:
        for m in s.mitigates:
            mitigated.add(m)
    unmitigated = [u for u in ursk if u.status != "Deprecated" and u.id not in mitigated]
    if unmitigated:
        ctx.log(f"WARN: {len(unmitigated)} URSK item(s) without any SRS.links.mitigates pointing at them")

    # Log file
    log_path = EXPORT_DIR / f"{identifiers['uef']}-{version_label}-use-export.log"
    header = [
        f"build_use_export run at {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"uef={identifiers['uef']} use={identifiers['use']} annex1={identifiers['annex1']}",
        f"version_label={version_label} date={identifiers['date']}",
        f"template_mode={template_mode}",
        "",
    ]
    log_path.write_text("\n".join(header + ctx.log_lines) + "\n", encoding="utf-8")
    for kind, (p, _md) in rendered.items():
        print(str(p))

    # Strict gate
    if args.strict and (total_todos or unmitigated):
        print(
            f"STRICT: {total_todos} [TODO] marker(s), {len(unmitigated)} URSK without "
            f"mitigation — failing",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
