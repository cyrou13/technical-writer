---
id: RSK-XXX-NNN
title: [TODO] short title ≤ 80 characters
status: Draft
version: 1.0.0
created: YYYY-MM-DD
updated: YYYY-MM-DD

# ISO 14971 risk category — picks which onglet of the risk table this item lives in
risk_category: Design          # Design | Production | Usability

# ISO 14971 §C.2 — context: where the risk originates
software_function: [TODO]      # high-level function affected, e.g. "CSpine image processing"
software_item: [TODO]          # module / file path contributing to the hazard

# ISO 14971 §C.2 — chain of causation
hazard: [TODO potential source of harm]
initiating_causes: |
  - [TODO cause 1]
  - [TODO cause 2 — independent triggers that can start the sequence]
foreseeable_sequence: |
  (1) [TODO initial event]
  (2) [TODO intermediate step]
  (3) [TODO event leading to the hazardous situation]
hazardous_situation: [TODO circumstance of exposure]
harm: [TODO envisaged damage]

# Initial risk estimate (before mitigation)
severity: Negligible           # Negligible | Minor | Serious | Critical | Catastrophic
probability: Remote             # Improbable | Remote | Occasional | Probable | Frequent
risk_level: Low                 # Low | Medium | High (qualitative, computed from matrix)
acceptable: true                # bool — true if no mitigation needed

# Risk control hierarchy — ISO 14971 §7.2
# inherent_design       : eliminate the hazard at design time (preferred)
# protective_measure    : add a barrier/check that prevents harm
# information_for_safety: warn the user in the IFU/labeling
control_hierarchy: inherent_design

# Residual risk (after mitigation) — re-evaluated once controls are in place
residual_probability: Improbable
residual_severity: Negligible
residual_risk_level: Low
residual_acceptable: true

# Cascade — risks newly created by this mitigation (ISO 14971 §7.5)
arising_risks: []                # list of RSK IDs, e.g. [RSK-AUTH-008]

# IFU disclosure — required only when control_hierarchy = information_for_safety
labeling_disclosure: null        # null or a verbatim string copied into the IFU

source:
  - [TODO path/to/file]
links:
  parent: []
---

## Hazard

[TODO Description of the hazard, anchored in the code or in the device
behavior. ISO 14971 §3.2: a potential source of harm.]

## Initiating causes

[TODO Causes that may trigger the foreseeable sequence. Each cause is
independent — any one of them can start the chain. Examples: user
error, hardware fault, network outage, malformed input, software defect.]

## Foreseeable sequence of events

[TODO ISO 14971 §C.2 — describe the chain from the initiating cause to
the hazardous situation. Numbered steps. The last step must be the
hazardous situation itself.]

## Hazardous situation

[TODO Circumstance in which the user or their data is exposed to the
hazard. Distinct from the harm — this is the condition that enables it.]

## Harm

[TODO Envisaged damage, as concrete as possible. Patient, user, data,
property, environment.]

## Initial risk justification

[TODO Why this severity and this probability? Cite evidence: incident
reports, field data, expert judgement, similar devices. The numerical
risk index is severity × probability against the matrix defined in
`dt-risk-plan.md` (or the QMS Risk Management Plan).]

## Risk controls

[TODO Informal list of intended controls; the formal controls live in
the SRS/SDS/TC items whose `links.mitigates: [<this ID>]`. State the
chosen `control_hierarchy` and justify why no higher-tier control is
practicable.]

## Residual risk justification

[TODO Why is the residual risk acceptable after the controls? If
controls reduce severity AND probability, explain each reduction. If
controls only reduce probability (typical for software), explain why
the residual severity stays acceptable.]

## Notes

[TODO Additional context, links to RSK items in `arising_risks`,
labeling text if `control_hierarchy = information_for_safety`.]
