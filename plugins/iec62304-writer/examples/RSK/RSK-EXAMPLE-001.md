---
id: RSK-EXAMPLE-001
title: Example — session hijacking via predictable OAuth2 state
status: Draft
version: 1.0.0
created: 2026-05-07
updated: 2026-05-07
hazard: Predictable OAuth2 state enabling CSRF on the callback
hazardous_situation: An attacker makes the victim visit a forged link
harm: Session hijacking, unauthorized access to the user account
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

An OAuth2 `state` generated non-cryptographically (e.g. timestamp,
counter) allows an attacker to predict the expected value at callback
and to fix the victim's session.

## Hazardous situation

The user clicks on a forged `/auth/callback?code=...&state=...` link
while already authenticated against the IdP.

## Harm

Session hijacking: the attacker gains access to the user account on the
application side.

## Level justification

Severity `Serious` (privacy breach + unauthorized access). Probability
`Remote` because it requires social engineering + an authenticated IdP.
Initial risk `Medium`, hence not acceptable without controls.

## Expected controls

- Cryptographic generation of `state` (≥ 256 bits of entropy).
- Strict verification at callback that the received `state` matches the
  `state` stored server-side and bound to the pre-auth session.
- PKCE `S256` as additional control.

The formal controls live in the items whose
`links.mitigates: [RSK-EXAMPLE-001]` — here `SDS-EXAMPLE-001` and
`TC-EXAMPLE-001`.

## Notes

Example item. Illustrates how SDS and TC mitigate a RSK and how the
coverage matrix reflects it.
