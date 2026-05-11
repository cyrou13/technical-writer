<!--
  Narrative framing sections of the Software Requirements Specification.
  These sections do NOT come from code — they come from the QMS, the
  Intended Use document, and the Risk Management File.

  `/doc-export` inlines the sections below at fixed anchors of the final
  deliverable (see anchors next to each H2). Any H2 not listed here is
  ignored. Edit by hand — no agent touches this file.

  Recognized sections:
    ## document-overview         → §1.1
    ## abbreviations             → §1.2.1 (free-form text or markdown table)
    ## glossary                  → §1.2.2
    ## intended-use              → §2.1.2
    ## warnings-and-precautions  → §2.1.3
    ## connected-devices         → §2.1.4
    ## personnel-and-training    → §2.x (placed after the main requirements)
    ## packaging                 → §2.x (placed after the main requirements)
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
