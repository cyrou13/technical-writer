---
name: production-risk-analysis
description: Référence AAMI TIR57 + IEC 81001-5-1 §6.1 + NIST SP 800-161 pour l'analyse des risques de production / supply chain d'un logiciel médical. À invoquer pour identifier les hazards de packaging / delivery / deployment / update et produire des items PRSK distincts des RSK design (runtime) et des THR cyber (network attacker).
---

## OUTPUT LANGUAGE — STRICT

Any artifact produced while applying this skill (PRSK items, derived
SRS, frontmatter values, body sections, `[GAP-PROD]` markers) MUST be
written in **English**, regardless of the user's conversational
language or any global `CLAUDE.md` instruction.

# Production risk analysis — référence

Cette analyse couvre la **fenêtre entre le build et le déploiement** :
les risques qui matérialisent un artefact corrompu, falsifié ou
indisponible au moment où il atteint l'utilisateur final. Elle est
**distincte** de :

- **RSK** (design risk, ISO 14971 §C) — risque de comportement runtime
  du logiciel, identifié depuis le code.
- **THR** (cyber threat, IEC 81001-5-1 / STRIDE) — risque d'attaque
  réseau ou applicative sur le logiciel en exécution.

PRSK modélise l'**intégrité de la chaîne de production** :
provenance, signature, immuabilité, supply chain.

## Cadre normatif

- **AAMI TIR57:2016** §5.3 — Production risk categories.
- **IEC 81001-5-1:2021** §6.1 — Production phase security activities.
- **IEC 62304** §6 — Software maintenance process (couvre les
  release / deployment activities).
- **NIST SP 800-161 rev. 1** — Cybersecurity Supply Chain Risk Management
  (C-SCRM). Non-obligatoire en MDR mais cohérent avec MDCG 2019-16.
- **FDA Premarket Cybersecurity Guidance (2023)** §VI.B — Production
  cybersecurity.

## Vocabulaire (AAMI TIR57)

- **Production artefact** — toute sortie du build pipeline (image
  conteneur, binaire, package npm/pypi, fichier de configuration signé).
- **Production phase** — étape du cycle de vie où l'artefact est
  généré, signé, distribué, ou mis à jour.
- **Supply chain compromise** — modification non autorisée d'un
  artefact ou d'une de ses dépendances entre la source et le déploiement.

## Production phases (axe principal de catégorisation)

| Phase | Champ `production_phase` | Périmètre |
|---|---|---|
| Build & sign | `Packaging` | Génération de l'image, signature, attestation SBOM |
| Transfer | `Delivery` | Transfert vers le registre, mise à disposition |
| Install | `Deployment` | Pull, vérification de signature, lancement |
| Maintain | `Update` | Patch, version bump, rollback, end-of-support |

Chaque PRSK doit porter exactement **une** phase ; un risque qui
s'étale doit être éclaté en plusieurs PRSK liés via `links.parent`.

## Catégories typiques de hazards production

1. **Tampering of artefact** — image conteneur falsifiée, package
   manifest modifié, signature contournée.
2. **Corruption during transfer** — hash mismatch, MITM, registre
   compromis.
3. **Supply chain compromise** — dépendance tierce malveillante,
   dependency confusion, typosquatting (npm, PyPI, Docker Hub).
4. **Signing failure** — clé de signature volée, KMS mal configuré,
   rotation manquante.
5. **Config drift** — secret rotaté sans propagation, environment
   variable absente en prod, helm chart désaligné.
6. **Update integrity** — patch downgrade attack, rollback vers une
   version vulnérable, blocage d'une mise à jour critique.
7. **Reproducibility loss** — build non-déterministe, dépendance
   non-épinglée, base image flottante.

## Sources à scanner (à appliquer dans l'agent)

L'agent `production-risk-analyst` doit parcourir systématiquement :

1. **Containerization** — `Dockerfile`, `Containerfile`, `*.Dockerfile`,
   `compose.yaml`, `docker-compose*.yml`.
2. **CI/CD workflows** — `.github/workflows/*.yml`, `.gitlab-ci.yml`,
   `Jenkinsfile`, `bitbucket-pipelines.yml`, `.circleci/config.yml`.
3. **Package manifests** — `package.json` (scripts section),
   `pyproject.toml`, `requirements.txt`, `Pipfile.lock`, `Gemfile`,
   `go.mod`, `Cargo.toml`.
4. **Deploy & infra** — `deploy/`, `k8s/`, `helm/`, `terraform/`,
   `ansible/`, `Makefile`, `*.sh` (`deploy.sh`, `release.sh`,
   `install.sh`).
5. **Signing & attestation** — recherche de `cosign`, `notary`,
   `sigstore`, `slsa`, `in-toto`, `gpg --sign`, attestation OIDC.
6. **SBOM tooling** — recherche de `syft`, `cyclonedx`, `spdx`,
   `dependency-track`.

Pour chaque artefact identifié, vérifier :
- Est-il signé ? Si non, hazard tampering candidat.
- Sa provenance est-elle attestée (SBOM) ? Si non, supply chain candidate.
- Le déploiement utilise-t-il un digest pinned ou un tag mutable ?
  Si tag → hazard tampering candidat.

## Échelles (réutilisées de ISO 14971 / risk-analysis)

PRSK utilise **les mêmes échelles** severity / probability que RSK :

- Severity : Negligible | Minor | Serious | Critical | Catastrophic
- Probability : Improbable | Remote | Occasional | Probable | Frequent
- Risk index = severity × probability (1..25)
- Risk level matrix : 1-4 → Low, 5-12 → Medium, 13-25 → High

La hiérarchie de contrôle ISO 14971 §7.2 s'applique :
- `inherent_design` — éliminer le risque à la conception du **processus**
  (ex. builds reproductibles, immutable infrastructure).
- `protective_measure` — barrière dans le pipeline (signature
  vérification, admission webhook, digest pinning, OIDC tokens).
- `information_for_safety` — documentation runbook + alerte opérateur.

## Forme d'une mitigation

Trois options, **toutes liées au PRSK via `links.mitigates`** :

- **SRS de mitigation** — exigence applicable au pipeline ou au runtime
  (ex. `SRS-DEPLOY-001 — admission webhook rejects unsigned images`).
- **SDS de mitigation** — décision de design infra (ex. `SDS-CI-002
  — release workflow uses Cosign + OIDC keyless signing`).
- **TC de mitigation** — test du pipeline (ex. `TC-RELEASE-001 —
  CI fails when image digest is not pinned in helm chart`).

## Schéma PRSK

Voir skill `items-store` pour les champs communs. Champs spécifiques PRSK :

| Champ | Type | Obligatoire | Notes |
|---|---|---|---|
| `production_phase` | enum | oui | Packaging \| Delivery \| Deployment \| Update |
| `asset_at_risk` | string | oui | Artefact / asset exposé (image, signing key, config…) |
| `hazard` | string | oui | ISO 14971 §3.2 |
| `initiating_causes` | block list | oui | Chaîne causale §C.2 |
| `foreseeable_sequence` | block scalar | oui | `(1) → (2) → ...` |
| `hazardous_situation` | string | oui | |
| `harm` | string | oui | |
| `severity` | enum | oui | Negligible..Catastrophic |
| `probability` | enum | oui | Improbable..Frequent |
| `risk_level` | enum | oui | Low \| Medium \| High |
| `acceptable` | bool | oui | Avant mitigation |
| `control_hierarchy` | enum | oui | inherent_design \| protective_measure \| information_for_safety |
| `residual_probability` | enum | oui | Re-évaluation post-mitigation |
| `residual_severity` | enum | oui | |
| `residual_risk_level` | enum | oui | |
| `residual_acceptable` | bool | oui | |

## Critère d'acceptabilité

Un PRSK est **traité** si :

- `risk_level: Low` ET `acceptable: true` (contrôle par construction
  du pipeline — ex. infra immuable par défaut), OU
- ≥ 1 item le mitige ET `residual_risk_level: Low` ET
  `residual_acceptable: true`.

Sinon, il apparaît dans `_to_implement.md` (nouveau groupe **F. Production**).

## Garde-fous Classe IIb / FDA

Pour les dispositifs Classe IIb (Avicenna, MDR Annex IX/X), la
production phase security est **fortement attendue** par le notified
body. Un PRSK avec `severity: Critical` ou `Catastrophic` non réduit
remet en cause la submission. Insérer `[GAP-PROD] §6.1 — production
risk not acceptable` dans le corps du PRSK et alerter.
