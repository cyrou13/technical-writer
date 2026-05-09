---
id: URSK-XXX-NNN
title: [TODO] titre court ≤ 80 caractères
status: Draft
version: 1.0.0
created: YYYY-MM-DD
updated: YYYY-MM-DD
use_scenario: USC-XXX-NNN              # USC parent
use_error: [TODO action ou inaction erronée de l'utilisateur]
hazard: [TODO source potentielle de dommage]
hazardous_situation: [TODO circonstance d'exposition au danger]
harm: [TODO dommage envisagé]
severity: Negligible       # Negligible | Minor | Serious | Critical | Catastrophic
likelihood: Remote         # Improbable | Remote | Occasional | Probable | Frequent
risk_level: Low            # Low | Medium | High (matrice ISO 14971)
acceptable: true           # avant mitigation
residual_acceptable: true  # après mitigation
source:
  - [TODO chemin/composant UI]
links:
  parent: []
  triggers: []             # IDs RSK safety déclenchés si l'erreur survient
---

## Use Error

[TODO description précise de l'action ou inaction utilisateur]

## Conditions favorables à l'erreur

[TODO ce qui rend l'erreur plus probable : libellés proches, défaut
ambigu, fatigue, multi-patient, etc.]

## Hazard et harm

[TODO hazard → harm, lien causal court]

## Justification de niveau

[TODO pourquoi cette severity, cette likelihood, ce risk_level]

## Contrôles attendus

(Hiérarchie ISO 14971 : élimination > mesure technique > information.)

- [TODO contrôle 1]
- [TODO contrôle 2]

Les contrôles formels vivent dans les items SRS/SDS/TC qui ont
`links.mitigates: [<cet ID>]`.

## Notes

[TODO contexte, références études d'usability, formation utilisateur]
