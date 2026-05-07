---
id: TC-EXAMPLE-001
title: Exemple — login redirige vers l'IdP avec state et PKCE
status: Draft
version: 1.0.0
created: 2026-05-07
updated: 2026-05-07
type: Integration
automated: true
test_id: src/auth/oauth.test.ts::login_flow_redirects_to_idp
source:
  - src/auth/oauth.test.ts
links:
  verifies:
    - SRS-EXAMPLE-001
  mitigates: []
preconditions:
  - IdP de test démarré sur localhost:9000
steps:
  - GET /auth/login sans cookie de session
expected:
  - 302 vers ${IDP_URL}/authorize
  - paramètres client_id, redirect_uri, state, code_challenge présents
---

## Préconditions

- IdP de test (mock) démarré sur `http://localhost:9000`.
- Variables d'env `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET` chargées.

## Étapes

1. Effectuer `GET /auth/login` sans cookie.
2. Récupérer la réponse HTTP.

## Résultats attendus

- Code 302.
- En-tête `Location` pointant `http://localhost:9000/authorize`.
- Query string contient `client_id`, `redirect_uri`, `state` (≥ 32
  caractères), `code_challenge`, `code_challenge_method=S256`.

## Notes

Item exemple. À supprimer ou remplacer.
