---
id: THR-XXX-NNN
title: [TODO] titre court ≤ 80 caractères
status: Draft
version: 1.0.0
created: YYYY-MM-DD
updated: YYYY-MM-DD
stride: [T]                            # S | T | R | I | D | E (peut être combiné)
attacker: external_unauth              # external_unauth | external_auth | internal | supply_chain | physical
asset: [TODO actif menacé]
likelihood: Low                        # Low | Medium | High
impact: Low                            # Low | Medium | High
risk_level: Low                        # Low | Medium | High (matrice 3×3 du skill)
acceptable: true                       # avant mitigation
residual_acceptable: true              # après mitigation
source:
  - [TODO chemin/fichier]
links:
  parent: []
  triggers: []                         # IDs RSK safety déclenchés si exploit
---

## Threat

[TODO description de la menace, ancrée dans le code]

## Asset menacé

[TODO actif compromis et nature de la compromission]

## Vecteur d'exploitation

[TODO comment l'attaquant exploite, depuis quelle position]

## Justification de niveau

[TODO pourquoi cette likelihood, cet impact]

## Contrôles attendus

- [TODO liste informelle ; les contrôles formels vivent dans les items
      SRS/SDS/TC qui ont `links.mitigates: [<cet ID>]`]

## Notes

[TODO contexte additionnel, références CVE/CWE, recommandation d'audit]
