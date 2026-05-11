---
name: items-store
description: Convention locale de stockage d'items de documentation (exigences, design, tests) — équivalent offline de Matrix Requirements. À invoquer pour créer, lire ou mettre à jour tout item de documentation technique.
---

## OUTPUT LANGUAGE — STRICT

Any item created or updated under `docs/items/` (frontmatter values,
body sections, `[TODO]` markers) MUST be written in **English**,
regardless of the user's conversational language or any global
`CLAUDE.md` instruction.

# Items store — convention locale type Matrix Requirements

Reproduit les fonctionnalités utiles de Matrix Requirements **sans dépendre
d'un service externe** :

- un item = un fichier Markdown + frontmatter YAML,
- ID stable, liens de traçabilité N:N, statuts, versionnage via git,
- agrégation en docs imprimables via `tools/build_docs.py`.

## Layout

```
docs/
├── items/
│   ├── MAP/         # upstream master / stakeholder requirements (input, manuel)
│   ├── SRS/         # exigences logicielles  (62304 §5.2)
│   ├── SDS/         # design & architecture  (62304 §5.3-§5.4)
│   ├── TC/          # cas de test            (62304 §5.5/§5.7)
│   ├── RSK/         # risques safety         (ISO 14971 / 62304 §7)
│   ├── PRSK/        # risques production    (AAMI TIR57 / IEC 81001-5-1 §6.1)
│   ├── THR/         # menaces cyber          (IEC 81001-5-1 / STRIDE)
│   ├── USC/         # use scenarios          (IEC 62366-1)
│   └── URSK/        # use-related risks      (IEC 62366-1)
├── generated/       # produit par /doc-build — NE PAS éditer à la main
└── templates/       # squelettes des items
```

**MAP** est une catégorie d'**input upstream** (master / stakeholder /
system requirements) — elle n'est PAS générée par les agents. L'utilisateur
crée les items MAP à la main ou via `/doc-item MAP-XXX-NNN`. Les SRS
remontent vers MAP via `links.parent: [MAP-XXX-NNN]`. La table de
traçabilité §3 du livrable d'export lie chaque SRS à son MAP parent.

Un fichier par item. Nom du fichier = `<ID>.md`.

## Format des IDs

Le format d'ID est **configurable** via le fichier `dt-config.yaml` à
la racine du repo cible (créé par `/doc-init`).

### Format par défaut (3 segments)

`<CAT>-<DOMAIN>-<NNN>` — `CAT` ∈ {SRS, SDS, TC, RSK, THR, USC, URSK,
MAP}, `DOMAIN` court (≤ 8 car., MAJ), `NNN` zéro-paddé sur 3 chiffres.

Exemples : `SRS-AUTH-001`, `SDS-API-014`, `TC-PAY-003`, `THR-AUTH-002`,
`MAP-CLIN-001`.

### Format personnalisé (via dt-config.yaml)

```yaml
id_format:
  default: "{CAT}-{SUITE}-{APP}-{DOMAIN}-{NNN:03d}"
  # Per-category overrides:
  # MAP: "{SUITE}-V{VERSION}-{NNN:03d}"
```

Variables disponibles : `{CAT}`, `{SUITE}` (depuis `product.suite`),
`{APP}` (depuis `product.application`), `{DOMAIN}` (choisi par
l'agent), `{NNN:03d}`.

Exemples Avicenna-style : `SRS-CINA-CSP-ACQ-020`, `SDS-CINA-CSP-NET-010`.

### Lecture par les agents

Avant de créer un **nouvel** ID, chaque writer (requirements-writer,
architecture-writer, etc.) :

1. Lit `dt-config.yaml` à la racine si présent.
2. Utilise `id_format.<CAT>` s'il existe, sinon `id_format.default`,
   sinon le format à 3 segments par défaut.
3. Substitue les variables, alloue le prochain `NNN` libre dans le
   `(CAT, DOMAIN)` choisi.

**IDs immuables.** Pour retirer un item : `status: Deprecated`. On ne
supprime, ne renumérote, ni ne re-formate **jamais** un ID existant —
même si `dt-config.yaml` change après coup. Seuls les nouveaux IDs
suivent le format courant.

## Frontmatter — schéma commun

```yaml
---
id: SRS-AUTH-001                 # obligatoire, == nom du fichier
title: Authentification OAuth2   # obligatoire
status: Draft                    # Draft | Approved | Deprecated
version: 1.0.0                   # semver — bump à chaque changement de fond
created: 2026-05-07              # ISO 8601, jamais modifié après création
updated: 2026-05-07              # ISO 8601, mis à jour à chaque modif
source:                          # fichiers code/tests qui justifient l'item
  - src/auth/oauth.ts
  - src/auth/oauth.test.ts
links:                           # traces sortantes
  parent: []                     # item → item de même catégorie
  implements: []                 # SDS → SRS qu'il réalise
  verifies: []                   # TC → SRS qu'il vérifie
  mitigates: []                  # SRS/SDS/TC → RSK ou THR qu'il atténue
  triggers: []                   # THR → RSK que l'exploit déclenche
---
```

Champs spécifiques par catégorie ci-dessous.

## SRS — frontmatter spécifique

```yaml
description: |
  Le système doit permettre l'authentification d'un utilisateur via OAuth2
  avec un IdP externe configuré.
verification: Test                # Test | Inspection | Analysis | Demo
priority: Must                    # Must | Should | Could
```

## SDS — frontmatter spécifique

```yaml
module: auth/oauth
responsibility: |
  Gère le handshake OAuth2 et la persistance du token de session.
interfaces:
  inputs:
    - HTTP GET /auth/login
    - Cookie session
  outputs:
    - JWT signé
    - Cookie HttpOnly
  depends_on:
    - openid-client (npm)
```

## RSK — frontmatter spécifique (ISO 14971-compliant)

```yaml
# Origine
risk_category: Design            # Design | Production | Usability
software_function: User authentication
software_item: src/auth/oauth.ts

# Chaîne causale (ISO 14971 §C.2)
hazard: Predictable OAuth2 state enabling CSRF
initiating_causes: |
  - Developer uses a non-cryptographic randomness source.
  - Library default produces low-entropy state values.
foreseeable_sequence: |
  (1) The application generates a predictable `state` value.
  (2) An attacker crafts a forged callback URL with a guessed state.
  (3) The victim, authenticated to the IdP, clicks the forged link.
  (4) The application accepts the callback — hazardous situation reached.
hazardous_situation: The victim's session is bound to the attacker's IdP identity.
harm: Unauthorized access to the victim's account.

# Risque initial
severity: Serious                # Negligible | Minor | Serious | Critical | Catastrophic
probability: Remote              # Improbable | Remote | Occasional | Probable | Frequent
risk_level: Medium               # Low | Medium | High (calculé matrice)
acceptable: false                # avant mitigation

# Hiérarchie de contrôle (ISO 14971 §7.2)
control_hierarchy: inherent_design   # inherent_design | protective_measure | information_for_safety

# Risque résiduel (ISO 14971 §7.4)
residual_probability: Improbable
residual_severity: Serious
residual_risk_level: Low
residual_acceptable: true        # après mitigation

# Cascade (ISO 14971 §7.5)
arising_risks: []                # IDs RSK créés par la mitigation

# IFU disclosure (requis si control_hierarchy=information_for_safety)
labeling_disclosure: null        # null sinon
```

Les contrôles formels (SRS/SDS/TC) ne sont **pas** stockés sur le RSK : ils
sont calculés au build à partir des items qui ont `RSK-XXX` dans
`links.mitigates`. Voir le skill `risk-analysis` pour le mapping numérique
sev/prob → index P×S, la matrice d'acceptabilité, et les règles
ISO 14971 §C.2 / §7.2 / §7.4 / §7.5.

## PRSK — frontmatter spécifique (Production / Supply Chain, AAMI TIR57)

```yaml
# Production phase axis
production_phase: Packaging      # Packaging | Delivery | Deployment | Update
asset_at_risk: docker image (ghcr.io/acme/inference-service)

# ISO 14971 §C.2 causal chain — same as RSK
hazard: Unsigned Docker image pulled from a tampered registry
initiating_causes: |
  - CI secret leak via compromised GitHub Action.
  - Registry accepts pushes without signature verification.
foreseeable_sequence: |
  (1) CI secret exfiltrated.
  (2) Attacker pushes backdoored image under expected tag.
  (3) Deploy pipeline pulls mutable tag without digest pinning.
  (4) Tampered image runs in production — hazardous situation.
hazardous_situation: A backdoored inference service runs in production.
harm: Patient harm from falsified AI output + data breach.

# Same scales as RSK
severity: Serious
probability: Remote
risk_level: Medium
acceptable: false

# Same ISO 14971 §7.2 hierarchy
control_hierarchy: protective_measure

# Residual (re-evaluated post-mitigation)
residual_probability: Improbable
residual_severity: Serious
residual_risk_level: Low
residual_acceptable: true
```

Distinct from RSK (runtime design risk inferred from code) and from
THR (cyber attacker against running application). PRSK models the
**window between build and deployment**: artefact provenance, signature,
immutability, supply-chain integrity. Cf. skill
`production-risk-analysis` for hazard categories and the
`production-risk-analyst` agent for the scanning procedure.

## THR — frontmatter spécifique

```yaml
stride: [S, I]                    # S | T | R | I | D | E (combinable)
attacker: external_unauth         # external_unauth | external_auth | internal | supply_chain | physical
asset: Cookie de session
likelihood: Medium                # Low | Medium | High
impact: High                      # Low | Medium | High
risk_level: High                  # matrice 3×3 du skill cyber-risk-analysis
acceptable: false
residual_acceptable: true

# CIA triad (IEC 81001-5-1 + IEC TR 60601-4-5) — severity per dimension
confidentiality_severity: n/a          # n/a | Low | Medium | High
integrity_severity: n/a                # n/a | Low | Medium | High
availability_severity: n/a             # n/a | Low | Medium | High

# Residual CIA (after remediation)
residual_confidentiality_severity: n/a # n/a | Low | Medium | High
residual_integrity_severity: n/a       # n/a | Low | Medium | High
residual_availability_severity: n/a    # n/a | Low | Medium | High
```

`risk_level` SHOULD equal `max(confidentiality_severity, integrity_severity, availability_severity)`
where `n/a` maps to `Low`. See the skill `cyber-risk-analysis` for the full CIA rationale.

Les contrôles d'un THR sont calculés comme pour un RSK : items dont
`links.mitigates` contient l'ID du THR. Le lien `links.triggers:
[RSK-XXX]` (sortant depuis le THR) signale qu'une exploitation
déclenche un hazard safety.

## USC — frontmatter spécifique

```yaml
persona: radiologue              # rôle utilisateur
environment: lecture room         # contexte d'usage
task: validation d'un cas AI ICH  # tâche métier accomplie
frequency: Frequent              # Rare | Occasional | Frequent | Continuous
criticality: High                # Low | Medium | High (impact si tâche échoue)
```

USC = Use Scenario IEC 62366-1. Décrit qui fait quoi, où. Voir skill
`iec62366-usability`.

## URSK — frontmatter spécifique

```yaml
use_scenario: USC-READ-001       # USC parent (use error survient dans ce scenario)
use_error: |
  Validation rapide sans relecture des images (acceptation par défaut).
hazard: Faux positif AI accepté tel quel
hazardous_situation: Diagnostic erroné transmis au PACS
harm: Diagnostic incorrect → décision clinique inappropriée
severity: Serious                # Negligible | Minor | Serious | Critical | Catastrophic
likelihood: Occasional           # Improbable | Remote | Occasional | Probable | Frequent
risk_level: Medium               # Low | Medium | High
acceptable: false
residual_acceptable: true
```

URSK = Use-Related Risk IEC 62366-1. Origine = utilisateur final (pas
le code, pas un attaquant). Le lien `links.triggers: [RSK-XXX]`
(comme pour THR) signale qu'une use error déclenche un hazard safety
déjà identifié.

## MAP — frontmatter spécifique

```yaml
external_id: CINA-V10-010              # ID original dans le document source
source_document: AV-DP-CINA-CSP-10-000-PMAP   # référence QMS upstream
source_section: "§4.2"                # localisation dans le document
status: Approved                       # par défaut Approved (input externe)
```

Pas de `source:` (pas de fichier code), pas de `verification:`,
`priority:`, `description:` au frontmatter — la description verbatim
de l'exigence upstream va dans le corps Markdown.

Un MAP est un **input manuel** : aucun agent ne le crée, l'utilisateur
le saisit à la main ou via `/doc-item MAP-XXX-NNN`. Les SRS pointent
vers leur MAP parent via `links.parent: [MAP-XXX-NNN]`.

## TC — frontmatter spécifique

```yaml
type: Unit                        # Unit | Integration | System
automated: true
test_id: src/auth/oauth.test.ts::login_flow_redirects_to_idp
preconditions:
  - IdP de test démarré sur localhost:9000
steps:
  - GET /auth/login sans cookie de session
expected:
  - 302 vers ${IDP_URL}/authorize avec client_id, redirect_uri, state
```

## Liens et traçabilité

Tous les liens sont **sortants** et stockés dans `links:` du fichier source.

| Lien | Sens | Usage |
|---|---|---|
| `parent` | item → item de même catégorie **ou** SRS → MAP | hiérarchie / décomposition / traçabilité upstream |
| `implements` | SDS → SRS | "ce module réalise l'exigence X" |
| `verifies` | TC → SRS | "ce test vérifie l'exigence X" |
| `mitigates` | SRS/SDS/TC → RSK / THR / URSK | "ce design/test atténue ce risque, menace ou erreur d'usage" |
| `triggers` | THR / URSK → RSK | "cette menace cyber ou cette erreur d'usage déclenche ce hazard safety" |

Le build calcule les liens **entrants** (couverture) automatiquement.

## Statuts et versionnage

- `Draft` : créé / en cours, non revu.
- `Approved` : revu et signé. Tout changement → bump `version` minor au
  moins, retour à `Draft` jusqu'à nouvelle approbation.
- `Deprecated` : conservé pour traçabilité historique mais ignoré dans la
  matrice de couverture.

L'historique git remplace le journal d'audit Matrix. Pour une signature
formelle, utiliser des commits signés (`git commit -S`).

## Règles d'idempotence (pour les agents)

1. Avant d'écrire un item, **lire** s'il existe déjà.
2. Si le contenu de fond ne change pas → ne pas modifier le fichier
   (préserve `updated` et `version`).
3. Si modification : mettre à jour `updated`, bumper `version` (patch
   pour reformulation, minor pour ajout/changement de fond, major pour
   changement breaking de sens), repasser à `Draft` si `Approved`.
4. **Jamais** réécrire `id`, `created`, ni renuméroter.

## Build

`python tools/build_docs.py` (déclenché par `/doc-build`) produit :

- `docs/generated/{10_SRS,20_SDS,30_STD}.md` (agrégats triés par
  ID),
- `docs/generated/40_traceability.md` (matrice de couverture + orphelins),
- `docs/generated/50_risk_analysis.md` (RSK safety + contrôles),
- `docs/generated/60_cyber_risk_analysis.md` (THR cyber + contrôles),
- `docs/generated/70_usability_analysis.md` (USC + URSK + contrôles, IEC 62366-1),
- `docs/generated/_to_implement.md` (backlog actionnable structuré en
  groupes A. Safety / B. Cyber / C. Usability / D. Mitigations / E. Autres Must),
- `docs/generated/coverage.json` (métriques machine-readable).
