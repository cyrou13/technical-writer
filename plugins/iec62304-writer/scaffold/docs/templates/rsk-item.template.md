---
id: RSK-XXX-NNN
title: [TODO] short title ≤ 80 characters
status: Draft
version: 1.0.0
created: YYYY-MM-DD
updated: YYYY-MM-DD
hazard: [TODO potential source of harm]
hazardous_situation: [TODO circumstance of exposure]
harm: [TODO envisaged damage]
severity: Negligible        # Negligible | Minor | Serious | Critical | Catastrophic
probability: Remote          # Improbable | Remote | Occasional | Probable | Frequent
risk_level: Low              # Low | Medium | High
acceptable: true             # before mitigation
residual_acceptable: true    # after mitigation (recomputed once controls are in place)
source:
  - [TODO path/to/file]
links:
  parent: []
---

## Hazard

[TODO description of the hazard, anchored in the code]

## Hazardous situation

[TODO circumstance in which the user or their data is exposed]

## Harm

[TODO envisaged damage, as concrete as possible]

## Level justification

[TODO why this severity, this probability, this risk level]

## Expected controls

- [TODO informal list of intended controls; formal controls live in the
      SRS/SDS/TC items whose `links.mitigates: [<this ID>]`]

## Notes

[TODO additional context]
