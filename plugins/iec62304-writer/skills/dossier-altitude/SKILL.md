---
name: dossier-altitude
description: Règles de niveau de détail (« altitude ») et de forme des livrables du dossier technique, calées sur un dossier Avicenna approuvé (CINA-CSpine) et arbitrées document par document. À appliquer avant d'écrire ou d'exporter un item MAP/SRS/SDS/TC/RSK ou un livrable, et par les agents requirements-writer, architecture-writer, risk-analyst, test-evidence-collector et doc-updater.
---

## OUTPUT LANGUAGE — STRICT

Every artifact produced while applying this skill is written in **English**.

## Why this skill exists

A docs-as-code pipeline drifts toward the code: every function, config key and
test becomes a sentence, and the technical file grows to several times the size
of an approved one without saying more to a reviewer. The rules below set the
altitude of each deliverable. They were arbitrated one document at a time
against an approved Avicenna technical file (reference: CINA-CSpine; review of
CINA-CTP V01, 2026-10-07). The reference sets form and altitude, not content: a
quantitative device keeps what makes it differ (rule marked *adapted*).

## Transverse rules (every deliverable)

- **No code in deliverable text.** No function, class, module or test name, no
  config key, no repository path, no CI job name, no internal ticket or
  decision code (`#152`, `I40`, `A1`). Values are written in clear with their
  unit ("3000 HU", "6 s"), never as the key that holds them.
- **No measured result outside a results document.** A plan, a glossary or a
  description never carries a verification figure (it goes stale at the next
  regeneration and reads as an unsupported claim).
- **No TODO, no "evidence still owed", no draft banner in a release export.**
- **One source per information.** A topic is written once, in the document that
  owns it; the others refer to it.

## PMAP — Project Master Plan (MAP items)

The PMAP states stakeholder needs. A MAP requirement is atomic, ≤ ~50 words,
names no implementation and no process step.

Requirement set (each one a MAP item; children re-parented accordingly):

| Group | Requirements |
|---|---|
| Intended function | the device function (inputs → outputs), thresholds stated as fixed when they are; decision-support positioning (*adapted*: a quantitative device keeps an explicit "no diagnosis, not the sole basis" requirement) |
| Input data | one requirement "Description of the input imaging data", 6–10 bullets in clinical values: SOP class / orientation, temporal coverage and inter-phase interval (dynamic studies), slice thickness, z coverage, patient age. No config key. Parent of the SRS input/IO/timing requirements |
| Context of use | six atomic requirements: container packaging; folder-based exchange with the host platform, no data stored; PHI replicated unmodified into the outputs; image identified by name, tags and digest; log file; configurable output language (English for validation) |
| Configuration | clinical thresholds fixed and version-identified; only deployment parameters settable by the integrator. Never "JSON / environment / CLI" |
| Security | integrity and confidentiality of the processed data and results, per IEC 81001-5-1. No threat list (threats live in the security plan / threat model) |
| Accompanying documents | six requirements: SOUP/COTS list, CVE analysis, user guide content (list of its sections), localisation, labels, integration documentation |
| Regulatory | one requirement: device class and rule (MDR Annex VIII), software safety class (IEC 62304 §4.3). No approval codes, no rationale (it lives in the development plan) |
| Performance | processing time on the reference host, within the labelled input bounds |

Not in the PMAP:
- process requirements (reproducible build, pinned dependencies, release and
  update control, non-regression) → PMP / development plan;
- requirements that describe excluded or hidden functionality in negative
  ("any other output shall be unreachable…") → delete; the outputs requirement
  is enough;
- predicate argumentation ("why this predicate", "known differences") → the
  performance/comparison report and the 510(k) summary. §Predicate keeps the
  identification block only. A similar-devices table may stay (*adapted*: a
  crowded field), without analysis prose.

Sections:
- **Glossary**: 4–6 one-line definitions of the domain terms only, no figure;
  ≈ 10 abbreviations. The PMAP glossary is the single source; SUM, UEF, USE refer
  to it.
- **Device description** (target ≈ 370 words): form and integration, input,
  outputs, declared thresholds. Processing in 2–3 sentences (what is computed,
  not the step chain — that is the SDD and Methods).

## Requirement cartouche (rendering)

Every requirement (MAP and SRS) is rendered as the approved cartouche: the
identifier on a grey band (bold navy), the title in italic navy indented, the
text in blue without spacing, a blank line, the version line in black at body
size, then a 6-pt grey closing rule after the version line or after the tables
that follow it, and a blank line. The pandoc `custom-style` names must equal the
style names of the reference document (`RequirementId`, …): pandoc maps them by
name, and a mismatch makes it append an empty twin style that Word renders
instead.

## Changelog of the rules

- 2026-10-07 — transverse rules, PMAP, requirement cartouche (CINA-CTP review,
  decisions S00.1–S00.11).
