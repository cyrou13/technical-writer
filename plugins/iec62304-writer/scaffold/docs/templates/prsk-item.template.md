---
id: PRSK-XXX-NNN
title: [TODO] short title ≤ 80 characters
status: Draft
version: 1.0.0
created: YYYY-MM-DD
updated: YYYY-MM-DD

# Production phase where the risk materialises
production_phase: Packaging      # Packaging | Delivery | Deployment | Update

# Asset exposed to the hazard
asset_at_risk: [TODO]            # docker image, signing key, config file, artifact, etc.

# ISO 14971 §C.2 — chain of causation
hazard: [TODO potential source of harm]
initiating_causes: |
  - [TODO cause 1]
  - [TODO cause 2 — independent triggers that can start the sequence]
foreseeable_sequence: |
  (1) [TODO initial event]
  (2) [TODO intermediate step]
  (3) [TODO event leading to the hazardous situation]
hazardous_situation: [TODO circumstance of exposure]
harm: [TODO envisaged damage]

# Initial risk estimate (before mitigation)
severity: Negligible             # Negligible | Minor | Serious | Critical | Catastrophic
probability: Remote              # Improbable | Remote | Occasional | Probable | Frequent
risk_level: Low                  # Low | Medium | High (qualitative, computed from matrix)
acceptable: true                 # bool — true if no mitigation needed

# Risk control hierarchy — ISO 14971 §7.2
# inherent_design       : eliminate the hazard at process design time (preferred)
# protective_measure    : add a barrier/check that prevents harm
# information_for_safety: warn the operator / deployment team
control_hierarchy: protective_measure

# Residual risk (after mitigation) — re-evaluated once controls are in place
residual_probability: Improbable
residual_severity: Negligible
residual_risk_level: Low
residual_acceptable: true

source:
  - [TODO path/to/Dockerfile]
  - [TODO .github/workflows/release.yml]
links:
  parent: []
---

## Hazard

[TODO Description of the hazard, anchored in a production artefact (Dockerfile,
CI/CD workflow, deploy script, package manifest). ISO 14971 §3.2: a potential
source of harm arising from the production / supply-chain process rather than
from runtime software behaviour.]

## Initiating causes

[TODO Causes that may trigger the foreseeable sequence. Each cause is
independent — any one of them can start the chain. Examples: compromised
upstream package registry, tampered base image, misconfigured CI secret,
dependency added without pinning, broken signing step.]

## Foreseeable sequence of events

[TODO ISO 14971 §C.2 — describe the chain from the initiating cause to
the hazardous situation. Numbered steps. The last step must be the hazardous
situation itself.]

## Hazardous situation

[TODO Circumstance in which a malicious or corrupted artefact reaches the
deployment target or the end-user. Distinct from the harm — this is the
condition that enables it.]

## Harm

[TODO Envisaged damage, as concrete as possible. Data integrity, patient safety,
service availability, supply-chain compromise propagation.]

## Initial risk justification

[TODO Why this severity and this probability? Reference threat intelligence,
past incidents, or industry guidance (AAMI TIR57, IEC 81001-5-1 §6.1).
Risk index = severity × probability mapped via the standard matrix.]

## Risk controls

[TODO Informal list of intended controls; the formal controls live in the
SRS/SDS/TC items whose `links.mitigates: [<this ID>]`. State the chosen
`control_hierarchy` and justify why no higher-tier control is practicable.
Typical controls: image signing (Cosign/Notary), pinned digests, SBOM
attestation, CI artifact integrity checks, reproducible builds.]

## Residual risk justification

[TODO Why is the residual risk acceptable after the controls? If controls
reduce probability (e.g. signed digest verification eliminates undetected
tampering), explain the reduction. Residual severity is typically unchanged.]

## Notes

[TODO Additional context: references to CI/CD configuration, SBOM tooling,
signing key management procedures, deployment runbook. Link to upstream
PRSK items if this risk cascades.]
