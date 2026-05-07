---
id: SDS-EXAMPLE-001
title: Exemple — module auth/oauth
status: Draft
version: 1.0.0
created: 2026-05-07
updated: 2026-05-07
module: src/auth/oauth
source:
  - src/auth/oauth.ts
links:
  parent: []
  implements:
    - SRS-EXAMPLE-001
  mitigates: []
interfaces:
  inputs:
    - HTTP GET /auth/login
    - HTTP GET /auth/callback
  outputs:
    - 302 vers IdP
    - Cookie session HttpOnly+Secure
  depends_on:
    - openid-client (npm)
    - jose (npm)
---

## Responsabilité

Gère le handshake OAuth2 Authorization Code + PKCE et la création de la
session signée à l'issue du callback.

## Interfaces

### Entrées
- `GET /auth/login` — sans cookie de session.
- `GET /auth/callback?code=...&state=...` — retour IdP.

### Sorties
- 302 vers `${IDP_URL}/authorize` avec paramètres OAuth2 + PKCE.
- Cookie `sid` HttpOnly + Secure + SameSite=Lax.

### Dépendances
- `openid-client`
- `jose` pour la vérification JWT

## Invariants

- `state` est généré cryptographiquement et lié au sid pré-session.
- Aucun token IdP n'est stocké côté client.

## Notes de design

PKCE imposé même quand le client est confidentiel — défense en profondeur.
