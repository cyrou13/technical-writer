---
id: RSK-EXAMPLE-001
title: Exemple — détournement de session via state OAuth2 prévisible
status: Draft
version: 1.0.0
created: 2026-05-07
updated: 2026-05-07
hazard: state OAuth2 prévisible permettant CSRF sur le callback
hazardous_situation: Un attaquant fait visiter un lien forgé à la victime
harm: Détournement de session, accès non autorisé au compte utilisateur
severity: Serious
probability: Remote
risk_level: Medium
acceptable: false
residual_acceptable: true
source:
  - src/auth/oauth.ts
links:
  parent: []
---

## Hazard

Un `state` OAuth2 généré non cryptographiquement (ex. timestamp,
incrément) permet à un attaquant de prédire la valeur attendue au
callback et de fixer la session de la victime.

## Hazardous situation

L'utilisateur clique sur un lien `/auth/callback?code=...&state=...`
forgé, dans un contexte où il est déjà authentifié sur l'IdP.

## Harm

Détournement de session : l'attaquant gagne accès au compte utilisateur
côté application.

## Justification de niveau

Sévérité `Serious` (atteinte vie privée + accès non autorisé). Probabilité
`Remote` car nécessite ingénierie sociale + IdP authentifié. Risque
initial `Medium`, donc non acceptable sans contrôle.

## Contrôles attendus

- Génération cryptographique du `state` (≥ 256 bits d'entropie).
- Vérification stricte au callback que le `state` reçu correspond au
  `state` stocké côté serveur lié à la session pré-auth.
- Contrôle PKCE `S256` en complément.

Les contrôles formels vivent dans les items qui ont
`links.mitigates: [RSK-EXAMPLE-001]` — ici `SDS-EXAMPLE-001` et
`TC-EXAMPLE-001`.

## Notes

Item exemple. Illustre comment SDS et TC mitigent un RSK et comment la
matrice de couverture le reflète.
