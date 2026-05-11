---
id: RSK-EXAMPLE-001
title: Example — session hijacking via predictable OAuth2 state
status: Draft
version: 2.0.0
created: 2026-05-07
updated: 2026-05-11

risk_category: Design
software_function: User authentication
software_item: src/auth/oauth.ts

hazard: Predictable OAuth2 state enabling CSRF on the callback
initiating_causes: |
  - Developer uses a non-cryptographic randomness source (e.g. timestamp, counter) for `state`.
  - Library default produces low-entropy state shorter than 128 bits.
foreseeable_sequence: |
  (1) The application generates a predictable `state` value at /auth/login.
  (2) An attacker, already authenticated against the IdP, crafts a callback URL with a guessed `state`.
  (3) The victim, while authenticated against the IdP, clicks the forged link.
  (4) The application accepts the callback and binds the attacker's identity to the victim's session — hazardous situation reached.
hazardous_situation: The victim's browser holds a session bound to the attacker's IdP identity, without the victim noticing.
harm: Unauthorized access to the victim's account, with the same privileges as the victim (data exfiltration, action on behalf of the victim).

severity: Serious
probability: Remote
risk_level: Medium
acceptable: false

control_hierarchy: inherent_design

residual_probability: Improbable
residual_severity: Serious
residual_risk_level: Low
residual_acceptable: true

arising_risks: []
labeling_disclosure: null

source:
  - src/auth/oauth.ts
links:
  parent: []
---

## Hazard

An OAuth2 `state` generated non-cryptographically allows an attacker to
predict the expected callback value and fix the victim's session. ISO
14971 hazard = "session integrity loss via predictable cross-site
request forgery token".

## Initiating causes

- The developer uses a non-cryptographic randomness source (e.g.
  `Date.now()`, an incremental counter) for the `state` parameter.
- A library default produces low-entropy state values (< 128 bits).

## Foreseeable sequence of events

(1) The application generates a predictable `state` value at the
    `/auth/login` redirect.

(2) An attacker, already authenticated against the IdP, crafts a
    callback URL `/auth/callback?code=...&state=<guessed>`.

(3) The victim — who is already authenticated against the IdP — clicks
    the forged link (phishing, embedded image, redirect chain).

(4) The application accepts the callback and binds the attacker's IdP
    identity to the victim's session. The hazardous situation is reached.

## Hazardous situation

The victim's browser holds a session bound to the attacker's IdP
identity, without the victim noticing. The victim's actions are now
attributed to the attacker; the attacker's data is exposed to the
victim's UI, and vice versa.

## Harm

Unauthorized access to the victim's account, with the same privileges
as the victim: data exfiltration, transactions on behalf of the victim,
audit log poisoning.

## Initial risk justification

Severity `Serious` — privacy breach + unauthorized access to clinical
or operational data; reversible only by full session invalidation +
incident communication. Probability `Remote` — requires the attacker
to be authenticated against the same IdP AND to phish the victim
successfully. Initial risk index = 3 × 2 = 6 → `Medium` per the
acceptability matrix → not acceptable without controls.

## Risk controls

Chosen `control_hierarchy: inherent_design` — the predictability is
eliminated at the design level rather than detected post-hoc.

- Cryptographic generation of `state` (≥ 256 bits of entropy via
  `crypto.randomBytes` / `secrets.token_urlsafe`).
- Strict verification at callback: the received `state` must match the
  `state` stored server-side and bound to the pre-auth session.
- PKCE `S256` as a complementary control (mitigates other CSRF vectors).

Formal controls live in the items whose `links.mitigates:
[RSK-EXAMPLE-001]` — here `SDS-EXAMPLE-001` and `TC-EXAMPLE-001`.
No higher-tier control (i.e. removing OAuth2 entirely) is practicable
because OAuth2 is mandated by the upstream MAP requirement.

## Residual risk justification

After controls, the predictability is eliminated entirely — an attacker
cannot guess the `state`. Residual probability drops to `Improbable`
(requires a brute-force search of the entropy space, infeasible).
Residual severity stays `Serious` because the impact of an unlikely
success is unchanged. Residual risk index = 3 × 1 = 3 → `Low` → acceptable.

## Notes

Example item. Illustrates the full ISO 14971 §C.2 causal chain
(`initiating_causes` → `foreseeable_sequence` → `hazardous_situation` →
`harm`) and the ISO 14971 §7.2 control hierarchy.
