---
id: THR-XXX-NNN
title: [TODO] short title ≤ 80 characters
status: Draft
version: 1.0.0
created: YYYY-MM-DD
updated: YYYY-MM-DD
stride: [T]                            # S | T | R | I | D | E (may be combined)
attacker: external_unauth              # external_unauth | external_auth | internal | supply_chain | physical
asset: [TODO threatened asset]
likelihood: Low                        # Low | Medium | High
impact: Low                            # Low | Medium | High
risk_level: Low                        # Low | Medium | High (3x3 matrix from the skill)
acceptable: true                       # before mitigation
residual_acceptable: true              # after mitigation
source:
  - [TODO path/to/file]
links:
  parent: []
  triggers: []                         # safety RSK IDs triggered if exploited
---

## Threat

[TODO description of the threat, anchored in the code]

## Threatened asset

[TODO asset compromised and the nature of the compromise]

## Exploitation vector

[TODO how the attacker exploits, from which position]

## Level justification

[TODO why this likelihood, this impact]

## Expected controls

- [TODO informal list; formal controls live in the SRS/SDS/TC items
      whose `links.mitigates: [<this ID>]`]

## Notes

[TODO additional context, CVE/CWE references, audit recommendation]
