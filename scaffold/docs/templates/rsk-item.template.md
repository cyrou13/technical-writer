---
id: RSK-XXX-NNN
title: [TODO] titre court ≤ 80 caractères
status: Draft
version: 1.0.0
created: YYYY-MM-DD
updated: YYYY-MM-DD
hazard: [TODO source potentielle de dommage]
hazardous_situation: [TODO circonstance d'exposition]
harm: [TODO dommage envisagé]
severity: Negligible        # Negligible | Minor | Serious | Critical | Catastrophic
probability: Remote          # Improbable | Remote | Occasional | Probable | Frequent
risk_level: Low              # Low | Medium | High
acceptable: true             # avant mitigation
residual_acceptable: true    # après mitigation (recalculé une fois les contrôles posés)
source:
  - [TODO chemin/fichier]
links:
  parent: []
---

## Hazard

[TODO description du danger ancré dans le code]

## Hazardous situation

[TODO circonstance dans laquelle l'utilisateur ou ses données sont exposés]

## Harm

[TODO dommage envisagé, le plus concret possible]

## Justification de niveau

[TODO pourquoi cette sévérité, cette probabilité, ce niveau de risque]

## Contrôles attendus

- [TODO liste informelle des contrôles visés ; les contrôles formels
      vivent dans les items SRS/SDS/TC qui ont `links.mitigates: [<cet ID>]`]

## Notes

[TODO contexte additionnel]
