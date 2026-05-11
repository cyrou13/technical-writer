---
id: TC-EXAMPLE-001
title: Example — login redirects to the IdP with state and PKCE
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
  mitigates:
    - RSK-EXAMPLE-001
    - THR-EXAMPLE-001
preconditions:
  - Test IdP started on localhost:9000
steps:
  - GET /auth/login with no session cookie
expected:
  - 302 to ${IDP_URL}/authorize
  - parameters client_id, redirect_uri, state, code_challenge present
---

## Preconditions

- Test IdP (mock) started on `http://localhost:9000`.
- Environment variables `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET` loaded.

## Steps

1. Perform `GET /auth/login` without a cookie.
2. Capture the HTTP response.

## Expected results

- 302 status code.
- `Location` header pointing to `http://localhost:9000/authorize`.
- Query string contains `client_id`, `redirect_uri`, `state` (≥ 32
  characters), `code_challenge`, `code_challenge_method=S256`.

## Notes

Example item. Delete or replace.
