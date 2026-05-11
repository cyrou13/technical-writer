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

# CIA triad (IEC 81001-5-1 + IEC TR 60601-4-5) — severity per dimension
confidentiality_severity: High         # session theft = full account confidentiality breach
integrity_severity: High               # attacker can drive session = integrity of all user actions
availability_severity: n/a             # XSS does not disrupt service availability

# Residual CIA (after remediation: HttpOnly + CSP + escaping + dep audit)
residual_confidentiality_severity: Low
residual_integrity_severity: Low
residual_availability_severity: n/a
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

## CIA impact analysis

### Confidentiality
High — the session cookie is the primary credential. If stolen, the attacker
gains read access to all data visible to the victim's account.

### Integrity
High — by driving the victim's browser silently, the attacker can perform
any state-changing action the victim is authorized to perform (submit forms,
update records, trigger workflows).

### Availability
Not affected — XSS does not prevent the application from responding to
legitimate requests; no denial-of-service vector from this threat.

## Notes

Example item. Demonstrates the safety/cyber separation: the same
`auth/oauth` module mitigates both a safety RSK (callback CSRF) and a
cyber THR (XSS), via shared SDS/TC items.
