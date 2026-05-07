---
name: items-store
description: Convention locale de stockage d'items de documentation (exigences, design, tests) — équivalent offline de Matrix Requirements. À invoquer pour créer, lire ou mettre à jour tout item de documentation technique.
---

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
│   ├── SRS/         # exigences logicielles  (62304 §5.2)
│   ├── SDS/         # design & architecture  (62304 §5.3-§5.4)
│   ├── TC/          # cas de test            (62304 §5.5/§5.7)
│   └── RSK/         # risques (optionnel)    (62304 §7)
├── generated/       # produit par /doc-build — NE PAS éditer à la main
└── templates/       # squelettes des items
```

Un fichier par item. Nom du fichier = `<ID>.md`.

## Format des IDs

`<CAT>-<DOMAIN>-<NNN>` — `CAT` ∈ {SRS, SDS, TC, RSK}, `DOMAIN` court (≤ 8
car., MAJ), `NNN` zéro-paddé sur 3 chiffres.

Exemples : `SRS-AUTH-001`, `SDS-API-014`, `TC-PAY-003`.

**IDs immuables.** Pour retirer un item : `status: Deprecated`, on ne
supprime ni ne renumérote jamais.

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
  parent: []                     # SRS générique → SRS détaillé, SDS → SDS
  implements: []                 # SDS → SRS qu'il réalise
  verifies: []                   # TC → SRS qu'il vérifie
  mitigates: []                  # SDS/TC → RSK qu'il atténue
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

## RSK — frontmatter spécifique

```yaml
hazard: state OAuth2 prévisible permettant CSRF
hazardous_situation: |
  L'utilisateur clique sur un lien forgé alors qu'il est connecté à l'IdP.
harm: Détournement de session, accès non autorisé au compte
severity: Serious                # Negligible | Minor | Serious | Critical | Catastrophic
probability: Remote              # Improbable | Remote | Occasional | Probable | Frequent
risk_level: Medium               # Low | Medium | High
acceptable: false                # avant mitigation
residual_acceptable: true        # après mitigation
```

Les contrôles ne sont **pas** stockés sur le RSK : ils sont calculés au
build à partir des items qui ont `RSK-XXX` dans `links.mitigates`. Voir
le skill `risk-analysis`.

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
| `parent` | item → item de même catégorie | hiérarchie SRS / décomposition |
| `implements` | SDS → SRS | "ce module réalise l'exigence X" |
| `verifies` | TC → SRS | "ce test vérifie l'exigence X" |
| `mitigates` | SDS/TC → RSK | "ce design/test atténue le risque X" |

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

- `docs/generated/{10_SRS,20_SDS,30_test_evidence}.md` (agrégats triés par
  ID),
- `docs/generated/40_traceability.md` (matrice de couverture + orphelins),
- `docs/generated/50_risk_analysis.md` (RSK + contrôles, statut
  d'implémentation/vérification de chaque contrôle),
- `docs/generated/_to_implement.md` (backlog actionnable des mitigations
  et exigences Must non encore implémentées/vérifiées),
- `docs/generated/coverage.json` (métriques machine-readable).
