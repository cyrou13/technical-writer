---
id: THR-EXAMPLE-001
title: Example — session theft via XSS in the SPA
status: Draft
version: 1.0.0
created: 2026-05-07
updated: 2026-05-07
stride: [S, I]
attacker: external_unauth
asset: Session cookie
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

Script injection in the frontend (unescaped user comment,
`dangerouslySetInnerHTML` attribute, compromised frontend dependency)
allows an attacker to execute JS in the SPA context and steal the
session cookie.

## Threatened asset

Session cookie (`sid`). If HttpOnly is missing, accessible from
`document.cookie`. Otherwise, the attacker can still drive the session
from the victim's browser.

## Exploitation vector

Unauthenticated Internet attacker. Injects an XSS payload through a
user-input field rendered as-is, or exploits a vulnerable frontend
dependency.

## Level justification

`Likelihood: Medium` — XSS remains a frequent defect and the exposure
is public. `Impact: High` — session theft = account takeover. Matrix →
`risk_level: High`. Not acceptable without mitigation.

## Expected controls

- Session cookie `HttpOnly` + `Secure` + `SameSite=Lax`.
- Strict CSP (`script-src 'self'`, no `unsafe-inline`).
- Systematic escaping in the frontend (framework + lint).
- Regular audit of frontend dependencies.

The formal controls live in the items whose
`links.mitigates: [THR-EXAMPLE-001]` — here `SDS-EXAMPLE-001` and
`TC-EXAMPLE-001` (same items as for the RSK example).

## Notes

Example item. Demonstrates the safety/cyber separation: the same
`auth/oauth` module mitigates both a safety RSK (callback CSRF) and a
cyber THR (XSS), via shared SDS/TC items.
