#!/usr/bin/env python3
"""Build the QMS-ready Software Design Description deliverable.

Equivalent of the Avicenna AV-DP-CINA-CSP-10-007-SDD-V04.docx.

Reads:
    dt-config.yaml                       (QMS metadata, signatories, refs)
    docs/dt-clinical-context.md          (narrative sections from QMS)
    docs/items/SDS/*.md                  (required — error if empty)
    docs/items/SRS/*.md                  (optional — used in §4.5/§4.6)
    docs/items/THR/*.md                  (optional — populates §4)
    package.json / pyproject.toml / requirements.txt (optional — §5.2)

Writes:
    docs/export/<identifier>-<version_label>-SDD.md
    docs/export/<identifier>-<version_label>-SDD.docx  (if pandoc + reference_docx)
    docs/export/<identifier>-<version_label>-sdd-export.log

Stdlib only. Python 3.12+.
"""

from __future__ import annotations

import argparse
import json
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
    section_with_fallback,
    todo_marker,
)

ROOT = Path.cwd()
CONFIG_PATH = ROOT / "dt-config.yaml"
CLINICAL_PATH = ROOT / "docs" / "dt-clinical-context.md"
ITEMS_DIR = ROOT / "docs" / "items"
EXPORT_DIR = ROOT / "docs" / "export"


# ---------------------------------------------------------------------------
# BuildContext + cover/intro builders (mirrored from build_srs_export.py with the
# SDD-specific tweaks).
# ---------------------------------------------------------------------------


@dataclass
class BuildContext:
    config: dict
    clinical: dict[str, str]
    sds: list[Item]
    srs: list[Item]
    thr: list[Item]
    log_lines: list[str] = field(default_factory=list)

    def log(self, msg: str) -> None:
        self.log_lines.append(msg)
        print(msg, file=sys.stderr)


def _section(ctx: BuildContext, anchor: str, hint: str) -> str:
    """Shortcut wrapping `section_with_fallback` with this context."""
    return section_with_fallback(
        ctx.clinical, anchor, hint, config=ctx.config, root=ROOT
    )


def fmt_signatory(ctx: BuildContext, role: str) -> str:
    approvals = (ctx.config.get("approvals") or {}) if ctx.config else {}
    entry = approvals.get(role) or {}
    name = entry.get("name") or "[TODO]"
    job = entry.get("role") or "[TODO]"
    return f"{name} — {job}"


def build_cover(ctx: BuildContext) -> list[str]:
    doc = (ctx.config.get("document") or {}) if ctx.config else {}
    title = doc.get("title") or "[TODO document.title]"
    # Adapt title: replace SRS → SDD, otherwise append " — Software Design Description"
    base_title = re.sub(
        r"\bSoftware Requirements Specification\b",
        "Software Design Description",
        str(title),
    )
    if base_title == title:
        base_title = f"{title} — Software Design Description"
    identifier = doc.get("identifier") or "[TODO document.identifier]"
    sdd_identifier = identifier.replace("SRS", "SDD") if "SRS" in identifier else f"{identifier}-SDD"
    version_label = doc.get("version_label") or "V01"
    date = doc.get("date") or "[TODO document.date]"
    return [
        f"# {base_title}",
        "",
        f"**Document identifier:** {sdd_identifier}  ",
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
        _section(ctx, "document-overview",
                 "One paragraph describing the SDD scope: software item, design phase, audience."),
        "",
        "## 1.2 Abbreviations and Glossary",
        "",
        "### 1.2.1 Abbreviations",
        "",
        _section(ctx, "abbreviations", "List of abbreviations used throughout this document."),
        "",
        "### 1.2.2 Glossary",
        "",
        _section(ctx, "glossary", "Domain glossary."),
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
        "SDS items follow the IEC 62304 §5.3-§5.4 design notation. Each item",
        "documents a software unit with its interfaces (inputs / outputs /",
        "dependencies), responsibilities and invariants. Traceability to",
        "requirements is held in `links.implements` (SRS IDs).",
        "",
        "---",
        "",
    ]
    return lines


# ---------------------------------------------------------------------------
# §2 General System Architecture
# ---------------------------------------------------------------------------


def build_section_2(ctx: BuildContext) -> list[str]:
    return [
        "# 2. General System Architecture",
        "",
        _section(
            ctx,
            "general-system-architecture",
            "Describe the general system architecture: deployment topology "
            "(on-prem / cloud / hybrid), main components (data sources, "
            "processing service, storage, output channels), and the data flow "
            "at the system level. One paragraph + an optional ASCII or Mermaid "
            "diagram.",
        ),
        "",
        "---",
        "",
    ]


# ---------------------------------------------------------------------------
# §3 Application Architecture
# ---------------------------------------------------------------------------


def _extract_section(body: str, header: str) -> str:
    """Return the body of a markdown section H2 (`## header`) until next H2 or EOF.

    Returns "" if the header isn't found.
    """
    pattern = rf"^##\s+{re.escape(header)}\s*$"
    m = re.search(pattern, body, flags=re.MULTILINE)
    if not m:
        return ""
    start = m.end()
    next_h2 = re.search(r"^##\s+", body[start:], flags=re.MULTILINE)
    end = start + next_h2.start() if next_h2 else len(body)
    return body[start:end].strip()


def build_rationale(ctx: BuildContext) -> list[str]:
    """§3.1 — aggregate `## Design notes` (or fallback `## Notes`) from SDS items."""
    lines = ["## 3.1 Rationale for software architecture decisions", ""]
    found = False
    for sds in sorted(ctx.sds, key=lambda i: i.id):
        if sds.status == "Deprecated":
            continue
        notes = _extract_section(sds.body, "Design notes")
        if not notes:
            notes = _extract_section(sds.body, "Notes de design")
        if not notes:
            notes = _extract_section(sds.body, "Notes")
        if notes:
            found = True
            lines += [f"### From `{sds.id}` — {sds.title}", "", notes, ""]
    if not found:
        lines.append("_(no design rationale section found in SDS items)_")
        lines.append("")
    return lines


def build_section_3(ctx: BuildContext) -> list[str]:
    lines = ["# 3. Application Architecture", ""]
    lines += build_rationale(ctx)
    lines += [
        "## 3.2 Hardware and Software Requirements",
        "",
        _section(
            ctx,
            "hardware-and-software-requirements",
            "List the minimum HW/SW requirements: CPU, RAM, GPU, OS, runtime, "
            "network, storage. Reference the deployment SOP.",
        ),
        "",
        "## 3.3 Processing Workflow",
        "",
        _section(
            ctx,
            "processing-workflow",
            "Describe the data processing workflow at the algorithm level "
            "(input → preprocessing → inference → postprocessing → output). "
            "Include data formats and timing constraints.",
        ),
        "",
        "## 3.4 Application Workflow",
        "",
        _section(
            ctx,
            "application-workflow",
            "Describe the application workflow: how the software receives, "
            "processes and delivers results to consumers (PACS, viewer, etc.). "
            "Cover startup, steady state, shutdown, error recovery.",
        ),
        "",
        "## 3.5 Software Design Description",
        "",
    ]
    lines += build_software_items(ctx)
    lines += build_software_units(ctx)
    lines += [
        "### 3.5.3 Error and exit code standardization",
        "",
        _section(
            ctx,
            "error-code-standardization",
            "List the standardised exit codes and error categories produced "
            "by the application. One table row per code with category, "
            "meaning, and recovery action.",
        ),
        "",
        "## 3.6 Class Diagram",
        "",
        _section(
            ctx,
            "class-diagram",
            "Insert the UML class diagram of the main software items. "
            "Tool: PlantUML / Mermaid / draw.io. Reference upstream SDS items.",
        ),
        "",
    ]
    lines += build_application_specific_design(ctx)
    lines += ["---", ""]
    return lines


def build_software_items(ctx: BuildContext) -> list[str]:
    """§3.5.1 — Main Software Items. One block per top-level SDS item."""
    lines = ["### 3.5.1 Main Software Items", ""]
    active = [s for s in ctx.sds if s.status != "Deprecated"]
    if not active:
        lines += ["_(no SDS items)_", ""]
        return lines
    for sds in sorted(active, key=lambda i: i.id):
        responsibility = _extract_section(sds.body, "Responsibility") or _extract_section(
            sds.body, "Responsabilité"
        ) or "[TODO responsibility]"
        impls = (sds.fm.get("links") or {}).get("implements") or []
        sources = sds.fm.get("source") or []
        lines += [
            f"**{sds.id}** — {sds.title}",
            "",
            f"- **Module:** `{sds.get('module') or '—'}`",
            f"- **Sources:** {', '.join(f'`{s}`' for s in sources) if sources else '—'}",
            f"- **Implements (SRS):** {', '.join(impls) if impls else '—'}",
            "",
            "**Responsibility:**",
            "",
            responsibility,
            "",
        ]
    return lines


def build_software_units(ctx: BuildContext) -> list[str]:
    """§3.5.2 — Software Units detail (interfaces + invariants + design notes)."""
    lines = ["### 3.5.2 Software Units", ""]
    active = [s for s in ctx.sds if s.status != "Deprecated"]
    for sds in sorted(active, key=lambda i: i.id):
        interfaces = sds.fm.get("interfaces") or {}
        inputs = interfaces.get("inputs") or [] if isinstance(interfaces, dict) else []
        outputs = interfaces.get("outputs") or [] if isinstance(interfaces, dict) else []
        deps = interfaces.get("depends_on") or [] if isinstance(interfaces, dict) else []
        invariants = _extract_section(sds.body, "Invariants") or "—"
        lines += [
            f"#### {sds.id}",
            "",
            "**Interfaces:**",
            "",
            f"- Inputs: {', '.join(str(i) for i in inputs) if inputs else '—'}",
            f"- Outputs: {', '.join(str(o) for o in outputs) if outputs else '—'}",
            f"- Dependencies: {', '.join(str(d) for d in deps) if deps else '—'}",
            "",
            "**Invariants:**",
            "",
            invariants,
            "",
        ]
    return lines


def build_application_specific_design(ctx: BuildContext) -> list[str]:
    """§3.7 — detailed design per SDS item (full body)."""
    lines = ["## 3.7 Application Specific Design", ""]
    active = [s for s in ctx.sds if s.status != "Deprecated"]
    if not active:
        lines += ["_(no SDS items)_", ""]
        return lines
    for sds in sorted(active, key=lambda i: i.id):
        # Render the SDS body with H2 → H4 demotion (we're under §3.7).
        body = re.sub(r"^##\s+", "#### ", sds.body, flags=re.MULTILINE)
        body = re.sub(r"^###\s+", "##### ", body, flags=re.MULTILINE)
        lines += [
            f"### 3.7.{1 + active.index(sds) if False else ''} {sds.id} — {sds.title}".rstrip(),
            "",
            body,
            "",
        ]
    return lines


# ---------------------------------------------------------------------------
# §4 Security Risk Assessment
# ---------------------------------------------------------------------------


def build_section_4(ctx: BuildContext) -> list[str]:
    active_thr = [t for t in ctx.thr if t.status != "Deprecated"]
    lines = [
        "# 4. Security Risk Assessment",
        "",
        "## 4.1 Security Objectives",
        "",
        _section(
            ctx,
            "security-objectives",
            "State the security objectives for the software: confidentiality "
            "of patient data, integrity of clinical results, availability of "
            "the inference service, authenticity of the operator, "
            "non-repudiation of clinical decisions.",
        ),
        "",
        "## 4.2 Security domains and attack paths identification",
        "",
    ]
    if active_thr:
        lines += [
            "| THR ID | STRIDE | Attacker model | Asset |",
            "|---|---|---|---|",
        ]
        for t in sorted(active_thr, key=lambda i: i.id):
            stride = t.get("stride")
            stride_str = ", ".join(stride) if isinstance(stride, list) else str(stride or "—")
            lines.append(
                f"| {t.id} | {stride_str} | {t.get('attacker') or '—'} | "
                f"{t.get('asset') or '—'} |"
            )
        lines.append("")
    else:
        lines += ["_(no THR items — run `/doc-62304` to populate)_", ""]

    lines += ["## 4.3 Threat models and mitigation", ""]
    if not active_thr:
        lines += ["_(no THR items)_", ""]
    else:
        for t in sorted(active_thr, key=lambda i: i.id):
            lines += [
                f"### {t.id} — {t.title}",
                "",
                f"- **STRIDE:** {', '.join(t.get('stride')) if isinstance(t.get('stride'), list) else (t.get('stride') or '—')}",
                f"- **Attacker:** {t.get('attacker') or '—'}",
                f"- **Asset:** {t.get('asset') or '—'}",
                f"- **CIA initial:** Conf={t.get('confidentiality_severity') or 'n/a'} · "
                f"Integ={t.get('integrity_severity') or 'n/a'} · "
                f"Avail={t.get('availability_severity') or 'n/a'}",
                f"- **CIA residual:** Conf={t.get('residual_confidentiality_severity') or 'n/a'} · "
                f"Integ={t.get('residual_integrity_severity') or 'n/a'} · "
                f"Avail={t.get('residual_availability_severity') or 'n/a'}",
                f"- **Residual acceptable:** {t.get('residual_acceptable')}",
                "",
            ]

    lines += [
        "## 4.4 Penetration testing and remote access",
        "",
        _section(
            ctx,
            "penetration-testing",
            "Describe the penetration testing strategy: scope, frequency "
            "(e.g. yearly + per major release), tools (Burp, ZAP, custom), "
            "remote access architecture (VPN / bastion / no remote), and "
            "retention of test reports.",
        ),
        "",
    ]

    # §4.5 User Authorisation — list SRS items in AUTH/AUTHZ domains
    auth_srs = [
        s for s in ctx.srs
        if s.status != "Deprecated"
        and re.search(r"-(AUTH|AUTHZ|AUTHN)-", s.id)
    ]
    lines += ["## 4.5 User Authorisation", ""]
    if auth_srs:
        for s in sorted(auth_srs, key=lambda i: i.id):
            lines += [f"- **{s.id}** — {s.title}", ""]
    else:
        lines.append(
            _section(
                ctx,
                "user-authorisation",
                "Describe the user authorisation model: roles, permissions, "
                "audit log of role changes. Reference SRS items in the AUTH "
                "domain. (No SRS-AUTH-* items detected in this repo.)",
            )
        )
        lines.append("")

    # §4.6 Cryptographic Functions — list SRS in CRYPTO/SEC domains
    crypto_srs = [
        s for s in ctx.srs
        if s.status != "Deprecated"
        and re.search(r"-(CRYPTO|SEC|CIPHER|HASH)-", s.id)
    ]
    lines += ["## 4.6 Cryptographic Functions", ""]
    if crypto_srs:
        for s in sorted(crypto_srs, key=lambda i: i.id):
            lines += [f"- **{s.id}** — {s.title}", ""]
    else:
        lines.append(
            _section(
                ctx,
                "cryptographic-functions",
                "List the cryptographic primitives used: algorithms (AES-GCM, "
                "RSA, Ed25519, etc.), key lengths, KMS provider, rotation "
                "policy. Reference SRS items in CRYPTO/SEC domain. (No "
                "SRS-CRYPTO-*/SEC-* items detected in this repo.)",
            )
        )
        lines.append("")

    # §4.7 Analysis and conclusion — auto stats
    n_thr = len(active_thr)
    n_thr_high = sum(1 for t in active_thr if t.get("risk_level") == "High")
    n_thr_unacceptable = sum(1 for t in active_thr if t.get("residual_acceptable") is False)
    lines += [
        "## 4.7 Analysis and conclusion",
        "",
        f"- Total active threats (THR): **{n_thr}**",
        f"- High-risk threats: **{n_thr_high}**",
        f"- Threats with residual NOT acceptable ⚠: **{n_thr_unacceptable}**",
        "",
    ]
    if n_thr_unacceptable == 0 and n_thr > 0:
        lines.append(
            "All identified threats are reduced to acceptable residual levels by the controls "
            "listed in §4.3. The security posture is consistent with IEC 81001-5-1 expectations "
            "for the device class."
        )
    elif n_thr_unacceptable > 0:
        lines.append(
            "⚠ Some threats have residual NOT acceptable. See `/doc-risk-export` for the full "
            "Risk Analysis Report and the remediation plan."
        )
    else:
        lines.append(
            _section(
                ctx,
                "security-conclusion",
                "Provide the security conclusion: overall posture, residual "
                "risks, link to the Risk Management File.",
            )
        )
    lines += ["", "---", ""]
    return lines


# ---------------------------------------------------------------------------
# §5 COTS Control and Identification
# ---------------------------------------------------------------------------


def detect_dependencies() -> list[tuple[str, str, str]]:
    """Return a list of (manifest_file, package_name, version) for direct deps.

    Scans the standard manifests at the repo root. Stops at the first
    manifest found (does not deduplicate across manifests). Returns
    [] if no manifest is present.
    """
    deps: list[tuple[str, str, str]] = []

    # Python
    pyproject = ROOT / "pyproject.toml"
    if pyproject.is_file():
        text = pyproject.read_text(encoding="utf-8")
        m = re.search(r"^\s*dependencies\s*=\s*\[(.*?)\]", text, re.MULTILINE | re.DOTALL)
        if m:
            for line in m.group(1).splitlines():
                line = line.strip().strip(",").strip().strip("'\"")
                if not line:
                    continue
                pkg = re.split(r"[<>=~!]", line, 1)
                name = pkg[0].strip()
                version = line[len(name):].strip() or "*"
                if name:
                    deps.append(("pyproject.toml", name, version))
        if deps:
            return deps

    req = ROOT / "requirements.txt"
    if req.is_file():
        for line in req.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            pkg = re.split(r"[<>=~!]", line, 1)
            name = pkg[0].strip()
            version = line[len(name):].strip() or "*"
            if name:
                deps.append(("requirements.txt", name, version))
        if deps:
            return deps

    # Node
    pkg_json = ROOT / "package.json"
    if pkg_json.is_file():
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return deps
        for name, version in (data.get("dependencies") or {}).items():
            deps.append(("package.json", name, version))
        for name, version in (data.get("devDependencies") or {}).items():
            deps.append(("package.json (dev)", name, version))

    return deps


def build_section_5(ctx: BuildContext) -> list[str]:
    deps = detect_dependencies()
    lines = [
        "# 5. COTS Control and Identification",
        "",
        "## 5.1 COTS Control",
        "",
        _section(
            ctx,
            "cots-control",
            "Describe the COTS control procedure: version pinning policy, "
            "supplier qualification, vulnerability monitoring (CVE feeds, "
            "Dependabot, Renovate), incident triage workflow. Reference "
            "the SBOM tooling (syft / cyclonedx) and the dependency review "
            "cadence.",
        ),
        "",
        "## 5.2 COTS Identification",
        "",
    ]
    if deps:
        lines += [
            "Direct dependencies detected from manifests at the repo root:",
            "",
            "| Manifest | Package | Version |",
            "|---|---|---|",
        ]
        for manifest, name, version in deps:
            lines.append(f"| {manifest} | `{name}` | `{version}` |")
        lines += [
            "",
            "_(Transitive dependencies are not listed here — use `syft` or `cyclonedx` "
            "to produce a full SBOM and reference it in §5.1.)_",
            "",
        ]
    else:
        lines += [
            todo_marker(
                "cots-identification",
                "No package manifest (pyproject.toml, requirements.txt, package.json) "
                "detected at the repo root. List the COTS components manually here, "
                "or run `syft` / `cyclonedx` to generate an SBOM.",
            ),
            "",
        ]
    lines += [
        "## 5.3 Contribution to hazardous situations",
        "",
        _section(
            ctx,
            "cots-hazards",
            "For each COTS component, identify the hazardous situations it "
            "may contribute to. Reference the relevant RSK items via "
            "`links.mitigates`.",
        ),
        "",
    ]
    return lines


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def render_markdown(ctx: BuildContext) -> str:
    parts: list[str] = []
    parts += build_cover(ctx)
    parts += build_revision_history(ctx)
    parts += build_introduction(ctx)
    parts += build_section_2(ctx)
    parts += build_section_3(ctx)
    parts += build_section_4(ctx)
    parts += build_section_5(ctx)
    return "\n".join(parts).rstrip() + "\n"


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


def count_todos(md: str) -> int:
    """Count yellow TODO markers (HTML <mark>[TODO ...]</mark>) plus bare [TODO ...] plain text."""
    return len(re.findall(r"<mark>\[TODO[^\]]*\]", md)) + len(
        re.findall(r"\[TODO[^\]]*\](?!</mark>)", md)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the QMS-ready Software Design Description.")
    parser.add_argument("--strict", action="store_true",
                        help="Exit 1 if any [TODO] marker remains in the deliverable.")
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
        print("WARN: dt-config.yaml not found — defaults with [TODO]", file=sys.stderr)

    clinical = load_clinical_context(CLINICAL_PATH)
    sds = load_items("SDS", ITEMS_DIR)
    if not sds:
        print("ERROR: no SDS items under docs/items/SDS/. Run /doc-62304 first.", file=sys.stderr)
        return 1
    srs = load_items("SRS", ITEMS_DIR)
    thr = load_items("THR", ITEMS_DIR)

    ctx = BuildContext(config=config, clinical=clinical, sds=sds, srs=srs, thr=thr)
    md = render_markdown(ctx)

    doc = (config.get("document") or {}) if config else {}
    identifier = str(doc.get("identifier") or "UNKNOWN").strip()
    identifier_sdd = identifier.replace("SRS", "SDD") if "SRS" in identifier else f"{identifier}-SDD"
    version_label = str(doc.get("version_label") or "V01").strip()
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    md_path = EXPORT_DIR / f"{identifier_sdd}-{version_label}-SDD.md"
    docx_path = EXPORT_DIR / f"{identifier_sdd}-{version_label}-SDD.docx"
    log_path = EXPORT_DIR / f"{identifier_sdd}-{version_label}-sdd-export.log"

    md_path.write_text(md, encoding="utf-8")
    ctx.log(f"OK: wrote {md_path.relative_to(ROOT)} ({md.count(chr(10))} lines)")

    n_todos = count_todos(md)
    ctx.log(f"Items: {len(sds)} SDS, {len(srs)} SRS, {len(thr)} THR")
    ctx.log(f"TODO markers in deliverable: {n_todos}")

    if not args.md_only:
        rendering = (config.get("rendering") or {}) if config else {}
        ref = rendering.get("reference_docx")
        ref_path = (ROOT / ref).resolve() if ref else None
        if ref_path or shutil.which("pandoc"):
            try_pandoc(md_path, docx_path, ref_path, ctx)
        else:
            ctx.log("INFO: pandoc unavailable and no reference_docx — skipping .docx")

    header = [
        f"build_sdd_export run at {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        f"identifier={identifier_sdd} version_label={version_label}",
        "",
    ]
    log_path.write_text("\n".join(header + ctx.log_lines) + "\n", encoding="utf-8")
    print(str(md_path))

    if args.strict and n_todos:
        print(f"STRICT: {n_todos} [TODO] markers remain — failing", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
