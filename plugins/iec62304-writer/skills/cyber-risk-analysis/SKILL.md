---
name: cyber-risk-analysis
description: Référence IEC 81001-5-1 + AAMI TIR57 + threat modeling STRIDE pour l'analyse de cybersécurité d'un logiciel médical. À invoquer pour identifier les threats, dériver les contrôles de sécurité, et produire des items THR distincts des RSK safety.
---

## OUTPUT LANGUAGE — STRICT

Any artifact produced while applying this skill (THR items, derived
SRS, frontmatter values, body sections, `[GAP-CYBER]` markers) MUST be
written in **English**, regardless of the user's conversational
language or any global `CLAUDE.md` instruction.

# Cyber risk analysis — référence

Cette analyse est **distincte** de l'analyse de risques safety
(ISO 14971 / 62304 §7) et complémentaire à elle. Cadre principal :

- **IEC 81001-5-1** — Security in the medical device software life
  cycle (équivalent cyber de 62304).
- **AAMI TIR57** — Principles for medical device security: risk
  management.
- **MDCG 2019-16** (UE) / **FDA Premarket Cybersecurity Guidance**
  (2023) — attentes régulateurs.

Une menace cyber peut **déclencher** un hazard safety. Dans ce cas,
l'item THR pointe le RSK via `links.triggers: [RSK-XXX]`. Inversement,
toute mitigation déclarée (SRS/SDS/TC `links.mitigates`) peut couvrir
indifféremment des THR ou des RSK.

## Vocabulaire (IEC 81001-5-1)

- **Asset** — bien à protéger (donnée, identité, fonction, infrastructure).
- **Threat** — événement adverse potentiel ciblant un asset.
- **Vulnerability** — faiblesse exploitable.
- **Attack** — exploitation effective ou tentative.
- **Security control** — mesure réduisant la vraisemblance ou
  l'impact d'une menace.
- **Residual risk** — risque restant après contrôles.

## Modèle d'attaquant

Pour chaque THR, préciser le **type** d'attaquant retenu :

| Type | Capacités présumées |
|---|---|
| `external_unauth` | Attaquant Internet sans compte |
| `external_auth` | Utilisateur légitime malveillant |
| `internal` | Employé / opérateur avec accès interne |
| `supply_chain` | Dépendance compromise (npm, PyPI, image) |
| `physical` | Accès physique au device / poste |

Class A typique : focus sur `external_unauth` + `external_auth`. Les
deux autres types sont pertinents si le SBOM ou le contexte d'usage
les rend plausibles.

## STRIDE — taxonomie

| Lettre | Catégorie | Propriété violée | Exemples concrets |
|---|---|---|---|
| **S** | Spoofing | Authenticity | Session fixée, JWT forgé, credentials replay |
| **T** | Tampering | Integrity | Mass-assignment, paramètre modifié en transit |
| **R** | Repudiation | Non-repudiation | Action utilisateur sans log auditable |
| **I** | Information disclosure | Confidentiality | Fuite via log, erreur verbose, side-channel |
| **D** | Denial of service | Availability | Boucle infinie, regex catastrophique, OOM |
| **E** | Elevation of privilege | Authorization | IDOR, RBAC bypass, missing authz check |

Appliquer STRIDE **systématiquement** à chaque entrée externe,
frontière de confiance, et asset sensible.

## Méthode (à appliquer dans l'agent)

1. **Identifier les assets**
   - Données : credentials, tokens de session, PII, données métier
     sensibles.
   - Fonctions : opérations à effet de bord critiques.
   - Infrastructure : config, secrets d'environnement, fichiers persistés.

2. **Identifier les entry points et frontières de confiance**
   - Routes HTTP, webhooks, websockets, CLI, lecture de fichiers
     utilisateur, variables d'environnement, input pubsub.

3. **Appliquer STRIDE par entry point**
   - Pour chaque point, parcourir S-T-R-I-D-E.
   - Pour chaque combinaison plausible, créer un THR.

4. **Couvrir le supply chain**
   - Lister les dépendances directes (`package.json`,
     `pyproject.toml`).
   - Sans base CVE locale : remonter au moins les dépendances les plus
     sensibles (auth, crypto, parsing) en `attacker: supply_chain`.
   - Si une base CVE est fournie ou si l'utilisateur lance
     `npm audit` / `pip-audit`, parser le résultat.

5. **Estimer likelihood × impact**
   - `likelihood` : `Low` / `Medium` / `High` selon : exposition
     (Internet vs interne), complexité d'exploitation, présence de
     pré-requis.
   - `impact` : `Low` / `Medium` / `High` selon : nombre d'utilisateurs
     affectés, nature de l'asset compromis, possibilité de propagation.
   - `risk_level` = matrice 3×3 (cf. plus bas).

6. **Lien vers safety**
   - Si la menace, en cas d'exploitation, peut causer un hazard safety
     (perte d'intégrité de donnée critique → décision incorrecte) →
     `links.triggers: [RSK-XXX]`.
   - Dans ce cas, le RSK lié doit aussi être créé / vérifié.

7. **Dériver les contrôles**
   - Préférer les contrôles techniques aux contrôles purement
     procéduraux.
   - Hiérarchie ISO 14971-like : élimination > mesures techniques >
     information utilisateur.
   - Créer des SRS de mitigation (`priority: Must`, `links.mitigates`).
   - Ajouter `links.mitigates` aux SRS/SDS/TC existants déjà
     protecteurs.

## Matrice de niveau de risque (3×3)

|              | Impact Low | Impact Medium | Impact High |
|---|---|---|---|
| **Likelihood Low**    | Low | Low | Medium |
| **Likelihood Medium** | Low | Medium | High |
| **Likelihood High**   | Medium | High | High |

`risk_level: High` non réductible → escalade auprès du système qualité.

## Schéma frontmatter THR

```yaml
id: THR-AUTH-001
title: Détournement de session via XSS
status: Draft
version: 1.0.0
created: 2026-05-07
updated: 2026-05-07
stride: [S, I]                         # une ou plusieurs lettres
attacker: external_unauth
asset: Session token
likelihood: Medium                     # Low | Medium | High
impact: High                           # Low | Medium | High
risk_level: High                       # Low | Medium | High
acceptable: false                      # avant mitigation
residual_acceptable: true              # après mitigation
source:
  - src/auth/oauth.ts
  - src/frontend/index.html
links:
  parent: []
  triggers: []                         # IDs RSK déclenchés si exploit
```

## Critère d'acceptabilité

Un THR est **traité** si :

- `risk_level: Low` ET `acceptable: true`, OU
- ≥ 1 item le mitige (SRS/SDS/TC `links.mitigates`) ET
  `residual_acceptable: true`.

Sinon, il apparaît dans `_to_implement.md` (groupe **B. Cyber**).

## CIA impact dimensions (IEC 81001-5-1)

### Why rate CIA separately from STRIDE

STRIDE classifies the **attack vector** — what the attacker does (spoof,
tamper, deny…). CIA measures the **impact on security properties** — what is
lost for the protected asset. The same STRIDE category can produce very
different CIA profiles depending on the asset (e.g., Spoofing a session token
hits Confidentiality + Integrity; Spoofing a log entry mainly hits Integrity).
Separating them matches the Avicenna cyber risk table (annex1-RISK-TABLE.xlsx
"Cybersecurity risk analysis" sheet) and aligns with IEC TR 60601-4-5.

### Allowed values

`n/a` | `Low` | `Medium` | `High`

`n/a` means the dimension is not affected by this threat. Example: a
Denial-of-Service threat typically has `confidentiality_severity: n/a` and
`integrity_severity: n/a`.

### Projection of CIA onto risk_level

`risk_level = max(C, I, A)` where `n/a` is treated as `Low`.

Mapping: `n/a` → Low, `Low` → Low, `Medium` → Medium, `High` → High.

This means a threat that scores `High` on any single CIA dimension yields
`risk_level: High`, regardless of lower scores on the others.

The existing `impact` field (Low/Medium/High) SHOULD equal `risk_level` once
CIA dimensions are filled — it remains for backward compatibility and for
humans who want a single "global impact" label before computing CIA.

### Typical STRIDE → CIA projection

This table is indicative. Always justify per-threat based on the actual asset.

| STRIDE | Confidentiality | Integrity | Availability |
|---|---|---|---|
| S — Spoofing | Medium–High (identity assumed) | High (actions authorized under wrong identity) | n/a |
| T — Tampering | n/a–Low | High (data altered) | Low–Medium (corrupted data may block processing) |
| R — Repudiation | Low (audit log missing) | High (non-repudiation broken) | n/a |
| I — Information disclosure | High | n/a | n/a |
| D — Denial of service | n/a | n/a | High |
| E — Elevation of privilege | High (elevated access) | High (authorized to modify anything) | Medium–High (can disrupt as admin) |

## Garde-fous

- **Pas d'invention.** Un THR doit pouvoir être rattaché à un fichier
  source ou à une dépendance présente dans le manifest.
- **Pas de scan vulnérabilité actif** depuis l'agent. Si l'utilisateur
  fournit une sortie d'`npm audit` / `pip-audit` / Snyk, la parser ;
  sinon ne pas spéculer sur des CVE.
- **Pas de duplication safety/cyber.** Un même hazard apparaît une
  seule fois : soit RSK (origine safety), soit THR (origine cyber). Le
  lien `triggers` connecte les deux quand pertinent.
