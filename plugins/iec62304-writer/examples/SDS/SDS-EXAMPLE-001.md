---
id: SDS-EXAMPLE-001
title: Example — auth/oauth module
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
  mitigates:
    - RSK-EXAMPLE-001
    - THR-EXAMPLE-001
interfaces:
  inputs:
    - HTTP GET /auth/login
    - HTTP GET /auth/callback
  outputs:
    - 302 to IdP
    - Session cookie HttpOnly+Secure
  depends_on:
    - openid-client (npm)
    - jose (npm)
---

## Responsibility

Handles the OAuth2 Authorization Code + PKCE handshake and the creation
of the signed session at the end of the callback.

## Interfaces

### Inputs
- `GET /auth/login` — no session cookie.
- `GET /auth/callback?code=...&state=...` — IdP return.

### Outputs
- 302 to `${IDP_URL}/authorize` with OAuth2 + PKCE parameters.
- Cookie `sid` HttpOnly + Secure + SameSite=Lax.

### Dependencies
- `openid-client`
- `jose` for JWT verification

## Invariants

- `state` is generated cryptographically and bound to the pre-session sid.
- No IdP token is stored client-side.

## Design notes

PKCE is enforced even when the client is confidential — defense in depth.
