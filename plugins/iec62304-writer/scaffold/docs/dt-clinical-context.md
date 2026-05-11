<!--
  Narrative framing sections of the Software Requirements Specification.
  These sections do NOT come from code — they come from the QMS, the
  Intended Use document, and the Risk Management File.

  `/doc-srs-export` inlines the sections below at fixed anchors of the final
  deliverable (see anchors next to each H2). Any H2 not listed here is
  ignored. Edit by hand — no agent touches this file.

  Recognized sections (consumed by /doc-srs-export — SRS deliverable):
    ## document-overview         → §1.1
    ## abbreviations             → §1.2.1 (free-form text or markdown table)
    ## glossary                  → §1.2.2
    ## intended-use              → §2.1.2
    ## warnings-and-precautions  → §2.1.3
    ## connected-devices         → §2.1.4
    ## personnel-and-training    → §2.x (placed after the main requirements)
    ## packaging                 → §2.x (placed after the main requirements)

  Additional sections (consumed by /doc-risk-export — Risk Report):
    ## end-users                            → §2.2 of Risk Report
    ## characteristics-affecting-safety     → §2.3 of Risk Report (ISO TR 24971)

  Additional sections (consumed by /doc-use-export — Usability Engineering File):
    ## medical-purpose                      → UEF §2.2.1
    ## patient-population                   → UEF §2.2.2
    ## application-environment              → UEF §2.2.4 (use environment)
    ## resource-requirements                → UEF §2.2.5 (hardware/software requirements)
-->

## document-overview

[TODO One short paragraph describing what THIS SRS document covers:
the software item, the lifecycle phase, and the scope. Cross-reference
the upstream Master Plan and the downstream Test Plan.]

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
