<!--
  Narrative sections inlined into the deliverables by the exporters.
  These sections do NOT come from code — they come from the QMS, the
  Intended Use document, and the Risk Management File. Each `## <anchor>`
  below is a section the exporters look up by its slug; any other H2 is
  ignored. Edit by hand — no agent touches this file except where stated.

  Everything in this file is EXPORTED: present tense, no dates, no
  `[TODO`/`[DRAFT`/`[GAP-` markers, no commit hashes, no competitor names.
  A `[TODO …]` left below shows in the working draft by design and blocks
  a `--release` export (TL-1). A remark you want to keep goes in an HTML
  comment like this one — the exporters strip it.

  Recognized sections (consumed by /doc-srs — SRS deliverable):
    ## document-overview         → §1.1
    ## abbreviations             → §1.2.1 (free-form text or markdown table)
    ## glossary                  → §1.2.2 — one term per concept, the labeling's term (TL-13)
    ## intended-use              → §2.1.2
    ## warnings-and-precautions  → §2.1.3
    ## connected-devices         → §2.1.4
    ## personnel-and-training    → §2.x (placed after the main requirements)
    ## packaging                 → §2.x (placed after the main requirements)

  Sections REQUIRED by the SDD export (/doc-sdd; store lint SL-6):
    ## general-system-architecture, ## run-states, ## architecture-rationale,
    ## security-global-view, ## security-multi-patient-view,
    ## security-updateability-view, ## security-use-case-views
  The architecture-writer fills the first three and drafts the four
  security views from the code; the security-analyst completes the views;
  a human reviews all six. Leave a section empty rather than invent.

  Additional sections (consumed by /doc-risk — Risk Analysis Report):
    ## end-users                            → §2.2 of the Risk Report
    ## characteristics-affecting-safety     → §2.3 of the Risk Report (ISO TR 24971)

  Software Design Description (consumed by /doc-sdd-export):
    ## general-system-architecture          → §2
    ## hardware-and-software-requirements   → §3.2
    ## processing-workflow                  → §3.3
    ## application-workflow                 → §3.4
    ## class-diagram                        → §3.6 (optional, after the generated decomposition figure)
    ## error-code-standardization           → §3.5.3
    ## cots-control                         → §5
    ## cots-hazards                         → §5
    ## security-objectives                  → §4.1
    ## cryptographic-functions              → §4
    ## user-authorisation                   → §4
    ## penetration-testing                  → §4
    ## security-conclusion                  → §4

  Software Test Plan (consumed by /doc-stp-export):
    ## test-environment-overview  ## tests-schedule-logic  ## test-tools
    ## test-data-doc  ## test-other-materials  ## test-installation
    ## tests-identification-strategy  ## data-recording  ## tests-schedule
    ## qualification

  Test description and report (consumed by /doc-stdr-export, /doc-str-export):
    ## test-preparation-environment  ## test-preparation-tools
    ## test-preparation-data  ## rationale-for-decisions
    ## automated-tests-platform  ## local-tests-platforms

  An H2 that is not on this list is IGNORED — the anchor set lives in
  tools/_lib.py: CLINICAL_ANCHORS. Add the anchor there before writing the
  section, or the text is silently dropped and the deliverable keeps its
  [TODO].

  Additional sections (consumed by /doc-use-export — Usability Engineering File):
    ## medical-purpose                      → UEF §2.2.1
    ## patient-population                   → UEF §2.2.2
    ## application-environment              → UEF §2.2.4 (use environment)
    ## resource-requirements                → UEF §2.2.5 (hardware/software requirements)

  Other anchors the STP / STDR / STR exporters recognise (optional):
    hardware-and-software-requirements, processing-workflow,
    application-workflow, error-code-standardization, class-diagram,
    cots-control, test-environment-overview, tests-identification-strategy,
    tests-schedule, qualification, test-preparation-data,
    test-preparation-environment, test-preparation-tools,
    automated-tests-platform, local-tests-platforms, rationale-for-decisions.
  A section may also be supplied from a QMS-managed file through
  `dt-config.yaml: external_resources`.

  Labeling anchors (`intended-use`, `warnings-and-precautions`) are never
  edited to make a lint finding go away: a contradiction between them and
  the SRS is a DECISION finding (DEC-1/2) for the product owner / RAQA.
-->

## document-overview

[TODO One short paragraph describing THE SOFTWARE ITEM, not this document.
This section is inlined verbatim into the SRS, the SDD, the STDR, the STR,
the Risk Analysis Report and the Usability Engineering File, each of which
states its own purpose in the sentence above it — so write nothing here that
is true of only one of them. Cover what the item is, what it is delivered as,
what is inside its boundary and what is outside. Cross-reference the upstream
Master Plan and the downstream Test Plan.]

## abbreviations

| Abbreviation | Meaning |
|---|---|
| [TODO] | [TODO] |

## glossary

[TODO Definitions of clinical / domain terms that appear in the
requirements but are not standard software engineering terminology.
Each entry: term — definition.]

## intended-use

[TODO Verbatim copy of the Intended Use statement from the QMS. Do
NOT rephrase. This text appears in §2.1.2 of the SRS and must match
the labeling and the regulatory submission word-for-word.]

## warnings-and-precautions

[TODO Verbatim copy of the Warnings, Precautions and Limitations
section from the IFU / labeling. Numbered list preferred.]

## connected-devices

[TODO Devices intended to be connected to operate as intended (e.g.
PACS, modality, viewer station, HL7 broker). One bullet per device,
state the interface and the protocol.]

## personnel-and-training

[TODO Required user role, training and qualification level. References
the labeling / IFU.]

## packaging

[TODO Software delivery format: installer, container image, OTA update,
USB key shipped to site. Reference the corresponding SOP.]

## end-users

[TODO Describe the end users of the device — role, training,
qualification, language, jurisdiction. ISO 14971 §C.2 requires this
to scope the foreseeable hazards.]

## characteristics-affecting-safety

[TODO Per ISO TR 24971:2020 §A, list the device characteristics that
affect safety:

- Intended use (clinical context, criticality, decision support level)
- Patient population (age, vulnerability, contraindications)
- Connected systems (PACS, modality, viewer, HL7 broker)
- Software dependencies (OS, libraries, OS services)
- User environment (lighting, fatigue, multi-patient context)
- Data sources and inputs (modality, reconstruction kernel, slice
  thickness, acquisition protocol)
- Outputs and their downstream consumers
- Operational lifetime, update and disposal strategy

Each characteristic should be one sentence stating the fact, with no
risk evaluation — that is done in the risk table.]

## medical-purpose

[TODO IEC 62366-1 §5.1 (a) — one short paragraph stating the
intended medical indication of the device. Distinct from
`intended-use` which is the verbatim labeling statement; this one
focuses on the clinical workflow goal (e.g. "assist hospital
networks and trained medical specialists in workflow triage by
flagging and communication of suspected positive findings
compatible with acute cervical spine fractures").]

## patient-population

[TODO IEC 62366-1 §5.1 (b) — the intended patient population.
Bullet list preferred:

- Age:       [e.g. ≥ 18 years old]
- Weight:    [e.g. not applicable]
- Health:    [e.g. see medical-purpose]
- Nationality: [e.g. multiple]
- Patient state: [e.g. no limitation]
- Exclusions: [e.g. presence of orthopedic hardware]

For pure-platform software with no direct patient interaction,
state "not applicable — the patient is not the user of the
platform; downstream clinical workflows define their own patient
populations.".]

## application-environment

[TODO IEC 62366-1 §5.1 (e) — the use environment. Group by
sub-axis:

**General**
- [e.g. Hospital]
- [e.g. Imaging centers]
- [e.g. Home with remote connection]

**Conditions of visibility**
- [e.g. Normal conditions for an office desktop application]

**Physical conditions**
- [e.g. Normal ambient conditions — radiology office / home]
- [e.g. Dark ambient conditions — reading room]

**Frequency of use**
- [e.g. Once a year up to 20+ times a day]

**Mobility**
- [e.g. Desktop PC, laptop, tablet, smartphone]

For platforms with multiple personas, repeat the block per
persona group.]

## resource-requirements

[TODO IEC 62366-1 §5.1 (f) and resource constraints — the minimum
hardware / software / network configuration required to operate
the device safely. Examples:

**CPU**
- [e.g. Intel/AMD x86_64 with SSE4.1/SSE4.2/AVX/AVX2/FMA support]
- [e.g. minimum 8 threads at 3.0+ GHz]

**RAM**
- [e.g. 16 GB minimum]

**Storage**
- [e.g. 500-800 MB per execution]

**Container / OS**
- [e.g. OCI 1.0 image format, Ubuntu 22.04 LTS recommended]
- [e.g. Docker or compatible runtime]

**Network**
- [e.g. DICOM C-STORE inbound/outbound on port 11112]
- [e.g. HTTPS to authentication provider]

**GPU**
- [e.g. not required — CPU-only execution]

For pure SaaS platforms, state the client-side requirements
(browser version, network bandwidth, screen resolution) AND the
server-side requirements separately.]

<!-- REQUIRED (SDD). The component diagram (Mermaid) and one paragraph per component: what it does, what it talks to. -->
## general-system-architecture

<!-- REQUIRED (SDD). The state machine of the software — idle, receiving, processing, exporting, error, maintenance — with entry and exit conditions and what is observable in each state. -->
## run-states

<!-- REQUIRED (SDD). Why the architecture is what it is. The module-level `## Design notes` roll up here; alternatives discarded; no dates. -->
## architecture-rationale

<!-- REQUIRED (SDD; FDA premarket cybersecurity guidance, global system view). One diagram with every network interface, port and protocol, every trust boundary and authentication point, each data store with its protection at rest and in transit, where secrets live. One paragraph per boundary. -->
## security-global-view

<!-- REQUIRED (SDD; multi-patient harm view). How one patient's data and results are isolated from another's on the same instance: session scope, identifiers, storage separation, cleanup, what a cross-patient failure would look like. -->
## security-multi-patient-view

<!-- REQUIRED (SDD; updateability / patchability view). How software and OTS updates are delivered, authenticated (signature), applied and rolled back; who can trigger one; device behaviour during an update; OTS end-of-life handling. -->
## security-updateability-view

<!-- REQUIRED (SDD; security use-case views). One diagram per security-relevant use case — ingest, export, administer, update, support access — showing the actors, the data crossing each boundary and the control that protects the crossing. -->
## security-use-case-views
