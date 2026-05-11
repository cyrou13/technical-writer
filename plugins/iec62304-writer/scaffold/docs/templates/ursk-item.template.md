---
id: URSK-XXX-NNN
title: [TODO] short title ≤ 80 characters
status: Draft
version: 1.0.0
created: YYYY-MM-DD
updated: YYYY-MM-DD
use_scenario: USC-XXX-NNN              # parent USC
use_error: [TODO erroneous user action or inaction]
hazard: [TODO potential source of harm]
hazardous_situation: [TODO circumstance of exposure to the hazard]
harm: [TODO envisaged damage]
severity: Negligible       # Negligible | Minor | Serious | Critical | Catastrophic
likelihood: Remote         # Improbable | Remote | Occasional | Probable | Frequent
risk_level: Low            # Low | Medium | High (ISO 14971 matrix)
acceptable: true           # before mitigation
residual_acceptable: true  # after mitigation
source:
  - [TODO path/to/UI/component]
links:
  parent: []
  triggers: []             # safety RSK IDs triggered if the error occurs
---

## Use error

[TODO precise description of the user action or inaction]

## Conditions favoring the error

[TODO what makes the error more likely: confusable labels, ambiguous
default, fatigue, multi-patient context, etc.]

## Hazard and harm

[TODO hazard → harm, short causal link]

## Level justification

[TODO why this severity, this likelihood, this risk_level]

## Expected controls

(ISO 14971 hierarchy: elimination > technical measure > information.)

- [TODO control 1]
- [TODO control 2]

The formal controls live in the SRS/SDS/TC items whose
`links.mitigates: [<this ID>]`.

## Notes

[TODO context, usability study references, user training]
