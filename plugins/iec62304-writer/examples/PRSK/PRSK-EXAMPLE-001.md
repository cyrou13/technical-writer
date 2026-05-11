---
id: PRSK-EXAMPLE-001
title: Example — Docker image tampering between build and deployment via compromised registry
status: Draft
version: 1.0.0
created: 2026-05-11
updated: 2026-05-11

production_phase: Delivery

asset_at_risk: docker image (ghcr.io/acme/inference-service)

hazard: Unsigned Docker image pulled from a registry that accepted a tampered push
initiating_causes: |
  - Container registry credentials are leaked via a compromised CI secret, allowing
    an attacker to push a malicious image under the expected tag.
  - The registry does not enforce push-time signature verification, accepting any
    image regardless of provenance.
foreseeable_sequence: |
  (1) A CI secret (GHCR_TOKEN or equivalent) is exfiltrated from the build pipeline
      (e.g. via a malicious third-party GitHub Action or a leaked .env file).
  (2) The attacker pushes a backdoored image to ghcr.io/acme/inference-service:latest,
      overwriting the legitimate tag without bumping the digest.
  (3) The deployment pipeline pulls the image by mutable tag (`:latest`) without
      verifying a Cosign signature or pinned digest.
  (4) The backdoored image is deployed to the production inference cluster —
      hazardous situation reached.
hazardous_situation: A tampered inference-service container is running in production,
  with the AI model replaced or augmented by attacker-controlled code, invisible
  to operators because the container tag is unchanged.
harm: Corruption of AI inference results (silent mislabelling of medical images),
  potential patient harm from downstream clinical decisions based on falsified output,
  and exfiltration of patient data processed by the inference service.

severity: Serious
probability: Remote
risk_level: Medium
acceptable: false

control_hierarchy: protective_measure

residual_probability: Improbable
residual_severity: Serious
residual_risk_level: Low
residual_acceptable: true

source:
  - .github/workflows/release.yml
  - deploy/k8s/inference-deployment.yaml
links:
  parent: []
---

## Hazard

An unsigned Docker image served from a container registry can be silently
replaced by an attacker who has obtained push credentials. The registry
tag `:latest` is a mutable pointer — it does not guarantee image
provenance. ISO 14971 hazard = "deployment of tampered medical-device
software artefact due to missing supply-chain integrity control".

This is a **production-phase** risk, distinct from design-time software
defects (RSK) and runtime cyber threats (THR). The attacker model is
supply-chain / insider: the compromise occurs between the CI build and
the production deployment, not during application runtime.

## Initiating causes

- A CI/CD secret (`GHCR_TOKEN`, `DOCKER_PASSWORD`) is exfiltrated via a
  malicious third-party GitHub Action, a leaked repository secret, or a
  misconfigured environment variable exposed in build logs.
- The container registry does not enforce push-time Cosign signature
  verification (OCI Referrers API not configured), so any authenticated
  push is accepted regardless of provenance.

## Foreseeable sequence of events

(1) An attacker obtains valid registry push credentials (exfiltration
    path: compromised Action, secret scanning miss, or leaked `.env`
    committed to a branch).

(2) The attacker pushes a backdoored image to
    `ghcr.io/acme/inference-service:latest`. The new image passes
    basic tag checks because the attacker holds valid push credentials.

(3) The deployment pipeline (`deploy/k8s/inference-deployment.yaml`)
    specifies `image: ghcr.io/acme/inference-service:latest` without a
    pinned digest (`@sha256:...`) and without Cosign signature
    verification in the admission webhook.

(4) Kubernetes pulls the new `:latest` image at the next rollout or
    pod restart. The tampered inference service container starts without
    any alert. Hazardous situation is reached.

## Hazardous situation

A backdoored inference-service pod is running in the production cluster.
Operators see a healthy pod with the expected tag and version label.
The AI model weights or pre/post-processing code have been silently
replaced, producing systematically altered output on every inference
request.

## Harm

1. **Patient safety** — Downstream clinical decisions (radiologist
   triage, worklist prioritisation) are based on falsified AI output.
   Missed pathology or false positives may lead to delayed or incorrect
   treatment. Severity matches ISO 14971 `Serious` (reversible harm,
   no direct patient fatality from software alone given human-in-the-loop
   review, but significant clinical impact).

2. **Data integrity** — Patient imaging data processed during the
   compromise period is exfiltrated if the backdoor includes a data
   egress channel.

3. **Regulatory** — A COTS/SaMD post-market change not submitted to the
   notified body — potential CE MDR article 120 / IVDR compliance breach.

## Initial risk justification

Severity `Serious` — falsified AI output reaching clinical workflow,
with potential patient harm and data breach. Probability `Remote` —
requires both a credential leak AND absence of signature checks; this
combination is non-trivial but has been observed in supply-chain attacks
(SolarWinds, XZ Utils, Docker Hub credential leaks 2019–2023). Initial
risk index = 3 × 2 = 6 → `Medium` per the standard matrix → not
acceptable without controls.

Reference: AAMI TIR57:2016 §5.3.4 (production risk), IEC 81001-5-1
§6.1 (production phase security).

## Risk controls

Chosen `control_hierarchy: protective_measure` — the risk cannot be
eliminated by inherent design (the registry distribution model is
mandated by the deployment architecture), so a protective barrier is
the highest achievable tier.

Controls (formal items link back via `links.mitigates: [PRSK-EXAMPLE-001]`):

1. **Image signing** — all release images are signed with Cosign
   (`cosign sign --key` or keyless OIDC) as part of the release
   workflow (`.github/workflows/release.yml`). The Kubernetes admission
   controller (Kyverno / Sigstore policy) rejects unsigned images.

2. **Pinned digest** — deployment manifests reference images by
   immutable digest (`@sha256:<digest>`), not by mutable tag. The
   digest is written by the CI pipeline after signing and committed
   to the GitOps manifest repository.

3. **CI secret rotation and OIDC** — registry authentication uses
   OIDC short-lived tokens (GitHub Actions OIDC → GHCR) rather than
   long-lived secrets, reducing the credential-leak surface.

4. **SBOM attestation** — a CycloneDX SBOM is generated and attached
   to the OCI image as an attestation, enabling post-deployment
   verification of included components.

## Residual risk justification

After controls, an attacker cannot push a replacement image without
possessing the Cosign signing key (hardware-backed, stored in a KMS)
AND forging a valid OCI attestation. The probability drops to
`Improbable` — the multi-factor barrier makes silent substitution
infeasible without access to both the registry credentials and the
KMS-backed signing key simultaneously.

Residual severity stays `Serious` — if controls were somehow bypassed,
the harm profile is unchanged. Residual risk index = 3 × 1 = 3 → `Low`
→ acceptable.

## Notes

Example item illustrating a PRSK (Production Risk) entry. PRSK is
distinct from:

- **RSK** (design risk, ISO 14971): arises from runtime software
  behaviour identified in the code-map.
- **THR** (cyber threat, IEC 81001-5-1 / STRIDE): models an attacker
  targeting the running application.

PRSK models the window **between build and deployment** — the
supply-chain integrity domain. The attacker model here is a
supply-chain adversary or malicious insider with CI access, not an
external network attacker.

Relevant standards: AAMI TIR57:2016 §5.3 (production risk categories),
IEC 81001-5-1:2021 §6.1 (production phase security activities),
NIST SP 800-161r1 (C-SCRM).
