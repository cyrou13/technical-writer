---
id: SRS-EXAMPLE-001
title: Example — OAuth2 authentication requirement
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
  parent:
    - MAP-EXAMPLE-001
  implements: []
  verifies: []
  mitigates: []
---

## Description

The system **shall** allow an unauthenticated user to initiate an OAuth2
Authorization Code flow via the configured IdP, and **shall** establish a
signed session upon successful callback.

## Acceptance criteria

- [ ] `GET /auth/login` redirects (302) to `${IDP_URL}/authorize` with
      `client_id`, `redirect_uri`, `state`, `code_challenge`.
- [ ] The `state` is stored server-side and verified at callback.
- [ ] On successful callback, an HttpOnly + Secure session cookie is set.
- [ ] On IdP failure, the user is redirected to `/login?error=...`.

## Notes

This item is an **example** shipped with the scaffolding. Delete or
replace once the real items are in place.
