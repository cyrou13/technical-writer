---
id: THR-EXAMPLE-001
title: Exemple — vol de session via XSS dans la SPA
status: Draft
version: 1.0.0
created: 2026-05-07
updated: 2026-05-07
stride: [S, I]
attacker: external_unauth
asset: Cookie de session
likelihood: Medium
impact: High
risk_level: High
acceptable: false
residual_acceptable: true
source:
  - src/auth/oauth.ts
  - src/frontend/index.html
links:
  parent: []
  triggers: []
---

## Threat

Injection de script dans le frontend (commentaire utilisateur non
échappé, attribut `dangerouslySetInnerHTML`, dépendance frontend
compromise) permet à un attaquant d'exécuter du JS dans le contexte de
la SPA et de voler le cookie de session.

## Asset menacé

Cookie de session (`sid`). Si HttpOnly absent, accessible depuis
`document.cookie`. Sinon, l'attaquant peut tout de même piloter la
session depuis le navigateur de la victime.

## Vecteur d'exploitation

Attaquant Internet non authentifié. Insère un payload XSS via un
champ utilisateur affiché tel quel, ou exploite une dépendance frontend
vulnérable.

## Justification de niveau

`Likelihood: Medium` — XSS reste un défaut fréquent et l'exposition
est publique. `Impact: High` — vol de session = takeover de compte.
Matrice → `risk_level: High`. Non acceptable sans mitigation.

## Contrôles attendus

- Cookie session `HttpOnly` + `Secure` + `SameSite=Lax`.
- CSP stricte (`script-src 'self'`, pas de `unsafe-inline`).
- Échappement systématique côté frontend (framework + lint).
- Audit régulier des dépendances frontend.

Les contrôles formels vivent dans les items qui ont
`links.mitigates: [THR-EXAMPLE-001]` — ici `SDS-EXAMPLE-001` et
`TC-EXAMPLE-001` (mêmes items que pour le RSK exemple).

## Notes

Item exemple. Démontre la séparation safety/cyber : le même module
`auth/oauth` mitige à la fois un RSK safety (CSRF callback) et un
THR cyber (XSS), via des items SDS/TC partagés.
