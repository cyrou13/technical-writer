---
id: SRS-EXAMPLE-001
title: Exemple — exigence d'authentification OAuth2
status: Draft
version: 1.0.0
created: 2026-05-07
updated: 2026-05-07
verification: Test
priority: Must
source:
  - src/auth/oauth.ts
  - src/auth/oauth.test.ts
links:
  parent: []
  implements: []
  verifies: []
  mitigates: []
---

## Description

Le système **doit** permettre à un utilisateur non authentifié d'initier
un flux OAuth2 Authorization Code via l'IdP configuré, et **doit**
établir une session signée à l'issue du callback.

## Critères d'acceptation

- [ ] `GET /auth/login` redirige (302) vers `${IDP_URL}/authorize` avec
      `client_id`, `redirect_uri`, `state`, `code_challenge`.
- [ ] Le `state` est stocké côté serveur et vérifié au callback.
- [ ] Au succès du callback, un cookie de session HttpOnly + Secure est
      posé.
- [ ] En cas d'échec d'IdP, l'utilisateur est redirigé vers `/login?error=...`.

## Notes

Cet item est un **exemple** livré avec le scaffolding. À supprimer ou
remplacer une fois que les vrais items sont en place.
