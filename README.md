# iec62304-writer

Plugin Claude Code pour générer et maintenir la documentation technique
IEC 62304 (Classe A) à partir d'un codebase TypeScript/JavaScript +
Python — **sans dépendance à un service externe**. Reproduit localement
les features utiles de Matrix Requirements (items à ID stable,
traçabilité N:N, matrice de couverture, statuts), avec analyses de
risques **safety** (ISO 14971) et **cyber** (IEC 81001-5-1 / STRIDE)
séparées.

## Installation

### Depuis GitHub (recommandé)

```bash
# Dans Claude Code, depuis n'importe quel repo :
/plugin marketplace add cyrou13/technical-writer
/plugin install iec62304-writer@iec62304-writer-marketplace
```

### Depuis un chemin local

```bash
/plugin install /chemin/vers/technical-writer
```

Puis dans le repo cible :

```bash
/doc-init                  # scaffolde tools/build_docs.py + docs/templates/
/doc-init --with-examples  # idem + items d'exemple liés
/doc-62304                 # pipeline complet : codemap → SRS/SDS/TC/RSK/THR → build → revue
```

## Livrables produits

| # | Fichier | Norme | Contenu |
|---|---|---|---|
| 10 | `docs/generated/10_SRS.md` | IEC 62304 §5.2 | Software Requirements |
| 20 | `docs/generated/20_SDS.md` | IEC 62304 §5.3-§5.4 | Design & architecture |
| 30 | `docs/generated/30_STD.md` | IEEE 829 / §5.5/§5.7 | Software Test Description |
| 40 | `docs/generated/40_traceability.md` | §5.1.1 / §5.2.6 | Matrice SRS↔SDS↔TC |
| 50 | `docs/generated/50_risk_analysis.md` | ISO 14971 / §7 | Risques safety |
| 60 | `docs/generated/60_cyber_risk_analysis.md` | IEC 81001-5-1 / STRIDE | Risques cyber |
| 70 | `docs/generated/70_usability_analysis.md` | IEC 62366-1 | Use scenarios + use-related risks |
| — | `docs/generated/_to_implement.md` | — | Backlog actionnable A/B/C/D/E |
| — | `docs/generated/coverage.json` | — | Métriques machine-readable |
| 99 | `docs/generated/99_compliance_review.md` | — | Revue de conformité |

## Composants du plugin

### Skills (référentiels et règles)

| Skill | Rôle |
|---|---|
| `iec62304-class-a` | Livrables 62304 Classe A et leur contenu minimal |
| `items-store` | Stockage local item-par-fichier (équivalent Matrix Requirements) |
| `srs-extract` | Extraction d'exigences depuis le code |
| `sds-generate` | Extraction de design et architecture |
| `test-evidence` | Découverte des tests, formalisation en TC |
| `test-plan` | Convention Software Test Description (STD) IEEE 829 |
| `traceability-matrix` | Spec de la matrice de couverture |
| `risk-analysis` | ISO 14971 + 62304 §7, hazards safety |
| `cyber-risk-analysis` | IEC 81001-5-1 + AAMI TIR57 + STRIDE |
| `iec62366-usability` | IEC 62366-1 — use scenarios, use-related risks, summative validation |

### Sub-agents

| Agent | Rôle |
|---|---|
| `code-archeologist` | Cartographie du repo → `docs/generated/_codemap.md` |
| `requirements-writer` | Génère `docs/items/SRS/*.md` |
| `architecture-writer` | Génère `docs/items/SDS/*.md` |
| `test-evidence-collector` | Génère `docs/items/TC/*.md` |
| `risk-analyst` | Génère `docs/items/RSK/*.md` + dérive les SRS de mitigation safety |
| `security-analyst` | Threat modeling STRIDE → `docs/items/THR/*.md` + mitigations cyber |
| `usability-analyst` | Scan UI → `docs/items/USC/*.md` + `URSK/*.md` + SRS-VIEWER-* + TC E2E |
| `doc-updater` | Détecte orphelins, items stale, gaps de couverture → `_update_diff.md` |
| `compliance-reviewer` | Revue 62304 Classe A → `99_compliance_review.md` |

### Slash commands

| Commande | Effet |
|---|---|
| `/doc-init [--update] [--with-examples]` | Scaffolde le repo cible |
| `/doc-62304 [scope]` | Pipeline complet (génération initiale) |
| `/doc-update [Vx.y]` | Mise à jour incrémentale après évolution du code (orphelins, stale, gaps) |
| `/doc-item <ID> [titre]` | CRUD d'un item unique |
| `/doc-build [--strict]` | Lance `tools/build_docs.py` |

## Layout du plugin

```
iec62304-writer/
├── .claude-plugin/
│   └── plugin.json
├── skills/                    # 9 skills
├── agents/                    # 7 sub-agents
├── commands/                  # 4 slash commands (dont /doc-init)
├── scaffold/                  # assets copiés par /doc-init
│   ├── tools/build_docs.py
│   └── docs/
│       ├── templates/         # 5 squelettes (SRS/SDS/TC/RSK/THR)
│       └── test_plan_intro.md # narrative STD (maintenu à la main)
└── examples/                  # items démo (copiés via --with-examples)
    ├── SRS/  SDS/  TC/  RSK/  THR/
```

## Layout produit dans le repo cible (après `/doc-init`)

```
mon-projet/
├── tools/
│   └── build_docs.py
└── docs/
    ├── templates/            # squelettes
    ├── items/                # source de vérité (édités à la main ou par les agents)
    │   ├── SRS/  SDS/  TC/  RSK/  THR/
    ├── test_plan_intro.md    # narrative du STD — édité à la main
    └── generated/            # produit par /doc-build (NE PAS éditer)
```

## Multi-repo (front + back, monorepo de repos)

Lance `/doc-init` depuis le **dossier projet** qui contient les
sous-repos git. Layout typique :

```
mon-projet/
├── front/                    # repo git #1
│   ├── .git/
│   ├── package.json
│   └── src/...
├── back/                     # repo git #2
│   ├── .git/
│   ├── pyproject.toml
│   └── api/...
├── tools/build_docs.py       # créé par /doc-init
└── docs/                     # créé par /doc-init
    ├── items/                #   items partagés entre les deux composants
    └── generated/
```

`/doc-init` détecte automatiquement les sous-dossiers contenant un
`.git/` et passe en mode multi-repo. Le `code-archeologist` produit
alors une code-map structurée par composant, et tous les agents
préfixent les chemins `source:` par le nom du composant
(`front/src/auth/oauth.ts`, `back/api/routes.py`).

`build_docs.py` scanne `package.json` / `pyproject.toml` /
`requirements*.txt` à la racine **et** dans chaque sous-repo détecté
pour produire la liste des frameworks de test dans le STD.

Le dossier projet n'a **pas besoin** d'être lui-même un repo git ; en
revanche, versionner `docs/` quelque part (3ᵉ repo umbrella, ou inclus
dans front/back) est conseillé pour la traçabilité 62304.

## Reproduction des features Matrix Requirements

| Matrix Requirements | Équivalent local |
|---|---|
| Items à ID stable, catégories | `docs/items/<CAT>/<ID>.md` |
| Liens UP/DOWN, traçabilité N:N | `links:` en frontmatter YAML |
| Coverage views | `40_traceability.md` + `coverage.json` |
| Item revisions / audit log | git history + commits signés |
| Workflow review/approve | `status: Draft → Approved`, PR + reviewers |
| Export DOCX/PDF | `pandoc docs/generated/*.md -o doc.pdf` |
| Item DOORS-like editing | `/doc-item <ID>` |

## Conventions clés

- **IDs immuables.** Une exigence retirée passe à `Deprecated`. Jamais
  renumérotée, jamais supprimée.
- **Pas d'invention.** Tout item doit être traçable à un fichier source.
  Sinon `[TODO]` explicite.
- **Idempotence.** Les agents préservent les IDs existants et bumpent
  `version` uniquement quand le contenu de fond change.
- **`docs/generated/` est régénérable.** Toute modification doit passer
  par `docs/items/`.
- **Safety vs cyber séparés.** RSK = ISO 14971 / patient ; THR =
  IEC 81001-5-1 / STRIDE. Lien `triggers` THR→RSK quand l'exploit cyber
  déclenche un hazard safety.

## CI

```yaml
- run: python tools/build_docs.py --strict
```

`--strict` échoue sur :

- marqueur `[TODO]`, `[GAP-62304]` ou `[GAP-CYBER]`,
- RSK avec `severity: Critical` ou `Catastrophic` (Classe A invalide),
- RSK ou THR avec `residual_acceptable: false`,
- RSK ou THR avec `acceptable: false` sans aucun contrôle.

## Limites v1

- Classe A uniquement. Pour B/C, dériver un skill `iec62304-class-b` et
  étendre les agents (intégration §5.6, gestion plus stricte des SOUP).
- Pas d'export DOCX/PDF intégré (`pandoc` à brancher).
- STD = description seule. Un Software Test Report (STR) parseur
  `junit.xml` / `pytest --json` reste possible en v2.
- Le `risk-analyst` infère les hazards depuis le code ; les hazards
  d'usage clinique restent à apporter par le système qualité.
- Le `security-analyst` ne lance pas de scan actif. Si un rapport
  `npm audit` / `pip-audit` / Snyk est fourni, il l'ingère ; sinon il
  recommande l'audit sans inventer de CVE.
