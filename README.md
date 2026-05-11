# iec62304-writer

Plugin Claude Code pour générer et maintenir la documentation technique
IEC 62304 (Classe A) à partir d'un codebase TypeScript/JavaScript +
Python — **sans dépendance à un service externe**. Reproduit localement
les features utiles de Matrix Requirements (items à ID stable,
traçabilité N:N, matrice de couverture, statuts), avec analyses de
risques **safety** (ISO 14971) et **cyber** (IEC 81001-5-1 / STRIDE)
séparées.

## Langue des artefacts générés

Tous les fichiers produits par le plugin sous `docs/` (items MAP / SRS /
SDS / TC / RSK / PRSK / THR / USC / URSK, agrégats
`docs/generated/*.md`, livrables `docs/export/*.{md,docx,csv,xlsx}`,
rapports de revue, markers `[TODO]`/`[GAP-...]`) sont **rédigés en
anglais**, indépendamment de la langue de la conversation avec
Claude Code. Cette contrainte est forcée à chaque couche (commandes,
sub-agents, skills, templates) pour garantir des livrables conformes
IEC 62304 dans la langue de référence des normes.

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
/doc-init                  # scaffolde tools/build_docs.py + dt-config.yaml + docs/templates/
/doc-init --with-examples  # idem + items d'exemple liés (MAP/SRS/SDS/TC/RSK/THR)
/doc-62304                 # pipeline complet : codemap → SRS/SDS/TC/RSK/THR → build → revue
/doc-srs-export                # livrable RAQA-ready (cover, signataires, traçabilité §3 → MAP)
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
| Export | `docs/export/<doc-id>-<vXX>-SRS.md` (+ `.docx` optionnel) | — | Livrable QMS-ready (cover signataires, revision history, §1 framing, §2 requirements, §3 traçabilité → MAP). Produit par `/doc-srs-export`. |

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
| `srs-export` | Spec du livrable SRS RAQA-ready à partir de `dt-config.yaml` + `dt-clinical-context.md` + items |
| `risk-report-export` | Spec du livrable Risk Analysis Report ISO 14971 — chaîne causale §C.2, hiérarchie de contrôle §7.2, résiduel quantitatif §7.4, cascade §7.5 |
| `production-risk-analysis` | Référence AAMI TIR57 + IEC 81001-5-1 §6.1 — risques de packaging/delivery/deployment/update (PRSK) |
| `risk-xlsx-export` | Spec du livrable Excel 4-onglets matching le format Avicenna `annex1-RISK-TABLE.xlsx` (dépendance `openpyxl`) |
| `sdd-export` | Spec du livrable Software Design Description (Avicenna `AV-DP-XXX-SDD`) |
| `stp-export` | Spec du livrable Software Test Plan (Avicenna `AV-DP-XXX-STP`) |
| `stdr-export` | Spec du livrable Software Test Description and Reports (Avicenna `AV-DP-XXX-STDR`) avec ingestion `test-results.json` |
| `str-export` | Spec du livrable Software Test Report synthétique (Avicenna `AV-DP-XXX-STR-auto`) |

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
| `production-risk-analyst` | Scan CI/CD + Docker + deploy → `docs/items/PRSK/*.md` + SRS-SIGNING/SBOM (AAMI TIR57) |
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
| `/doc-srs-export [--strict] [--md-only]` | Produit le livrable SRS QMS-ready dans `docs/export/` via `tools/build_srs_export.py` |
| `/doc-risk-export [--strict] [--md-only]` | Produit le Risk Analysis Report ISO 14971-compliant (+ table CSV d'inventaire) dans `docs/export/` via `tools/build_risk_export.py` |
| `/doc-risk-xlsx [--strict]` | Produit l'inventaire Excel 4-onglets (Design / Production / Usability / Cybersecurity) matching le format Avicenna `annex1-RISK-TABLE.xlsx` via `tools/build_risk_xlsx.py` (nécessite `openpyxl`) |
| `/doc-sdd-export [--strict] [--md-only]` | Produit le Software Design Description (Avicenna `AV-DP-XXX-SDD`) via `tools/build_sdd_export.py` |
| `/doc-stp-export [--strict] [--md-only]` | Produit le Software Test Plan (Avicenna `AV-DP-XXX-STP`) via `tools/build_stp_export.py` |
| `/doc-stdr-export [--strict] [--md-only]` | Produit le Software Test Description and Reports (Avicenna `AV-DP-XXX-STDR`) — ingère `test-results.json` produit par CI — via `tools/build_stdr_export.py` |
| `/doc-str-export [--strict] [--md-only]` | Produit le Software Test Report (Avicenna `AV-DP-XXX-STR-auto`) synthèse pass/fail depuis `test-results.json` — via `tools/build_str_export.py` |
| `/doc-migrate [--apply] [--stdout]` | Audit de migration après upgrade du plugin : détecte les clés manquantes dans dt-config.yaml, les anchors manquants dans dt-clinical-context.md, les items au schéma incomplet, et les scripts outdated. Mode additif-only (`--apply`) ou dry-run (défaut). |

## Layout du plugin

```
iec62304-writer/
├── .claude-plugin/
│   └── plugin.json
├── skills/                    # 17 skills (référentiels + exports)
├── agents/                    # 10 sub-agents
├── commands/                  # 12 slash commands
├── scaffold/                  # assets copiés par /doc-init
│   ├── tools/
│   │   ├── _lib.py                  # helpers partagés (YAML parser, Item, ...)
│   │   ├── build_docs.py            # agrégats internes /doc-build
│   │   ├── build_srs_export.py      # /doc-srs-export
│   │   ├── build_sdd_export.py      # /doc-sdd-export
│   │   ├── build_stp_export.py      # /doc-stp-export
│   │   ├── build_stdr_export.py     # /doc-stdr-export (ingère test-results.json)
│   │   ├── build_str_export.py      # /doc-str-export (idem)
│   │   ├── build_risk_export.py     # /doc-risk-export (.md + .csv)
│   │   └── build_risk_xlsx.py       # /doc-risk-xlsx (Excel 4-onglets)
│   ├── dt-config.yaml         # config QMS (signataires, refs, id_format, external_resources) — édité à la main
│   ├── test-results.example.json    # spec du format CI consommé par stdr/str-export
│   └── docs/
│       ├── templates/         # 9 squelettes (MAP/SRS/SDS/TC/RSK/PRSK/THR/USC/URSK)
│       ├── dt-clinical-context.md   # narratives QMS — édité à la main
│       └── test_plan_intro.md       # narrative STD (legacy, intégré dans 30_STD)
└── examples/                  # items démo (copiés via --with-examples)
    └── MAP/  SRS/  SDS/  TC/  RSK/  PRSK/  THR/
```

## Layout produit dans le repo cible (après `/doc-init`)

```
mon-projet/
├── tools/                          # tous copiés par /doc-init
│   ├── _lib.py                     # helpers partagés
│   ├── build_docs.py               # agrégats internes
│   ├── build_srs_export.py
│   ├── build_sdd_export.py
│   ├── build_stp_export.py
│   ├── build_stdr_export.py
│   ├── build_str_export.py
│   ├── build_risk_export.py
│   └── build_risk_xlsx.py
├── dt-config.yaml                  # config QMS — édité à la main
├── test-results.example.json       # exemple format CI — à remplacer par test-results.json en CI
└── docs/
    ├── templates/                  # 9 squelettes
    ├── items/                      # source de vérité
    │   ├── MAP/                    # ★ inputs upstream (master / stakeholder reqs) — saisis à la main
    │   ├── SRS/  SDS/  TC/
    │   ├── RSK/  PRSK/  THR/       # ★ risk safety / production / cyber
    │   └── USC/  URSK/             # ★ usability
    ├── dt-clinical-context.md      # narratives QMS — édité à la main
    ├── generated/                  # produit par /doc-build (NE PAS éditer)
    └── export/                     # produit par /doc-*-export — livrables QMS-ready
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
| Export DOCX intégré | `/doc-srs-export`, `/doc-sdd-export`, `/doc-stp-export`, `/doc-stdr-export`, `/doc-str-export`, `/doc-risk-export` (pandoc invoqué automatiquement si `rendering.reference_docx` est configuré) |
| Export Excel (inventory) | `/doc-risk-xlsx` (4-onglets Design/Production/Usability/Cybersecurity) |
| Item DOORS-like editing | `/doc-item <ID>` |

## Recette de reprise sur un projet existant

Si le plugin a été mis à jour depuis la dernière initialisation du projet,
lance d'abord `/doc-migrate` pour identifier les écarts :

```
/doc-migrate           # dry-run — rapport dans docs/generated/migration-report.md
/doc-migrate --apply   # applique les changements additifs (A+B uniquement)
/doc-init --update     # refresh les scripts tools/build_*.py si section D le signale
```

`/doc-migrate` est additif-only : il n'écrase jamais le contenu existant de
`dt-config.yaml`, `docs/dt-clinical-context.md`, ni aucun item.

## Workflow complet (code → livrable RAQA)

```
 1. /doc-init                       # scaffolde tout (dt-config.yaml, templates, tools)
 2. Éditer dt-config.yaml           # signataires, identifier, revision history, id_format,
                                    # external_resources (pointeurs Obsidian/QMS), test_results_path
 3. Saisir docs/items/MAP/*.md      # master reqs upstream (recopiés du PMAP) — manuel
 4. Éditer docs/dt-clinical-context.md  # intended use, warnings, glossaire, end-users,
                                    # characteristics-affecting-safety, etc. — manuel
 5. /doc-62304                      # génère SRS/SDS/TC/RSK/PRSK/THR/USC/URSK depuis le code
 6. /doc-update (occasionnel)       # après évolution du code

 7. /doc-srs-export                 # SRS    — docs/export/<id>-<vXX>-SRS.md  (+ .docx)
 8. /doc-sdd-export                 # SDD    — docs/export/<id>-<vXX>-SDD.md  (+ .docx)
 9. /doc-stp-export                 # STP    — docs/export/<id>-<vXX>-STP.md  (+ .docx)
10. /doc-risk-export                # Risk Report — (.md + .docx + .csv inventory)
11. /doc-risk-xlsx                  # Risk Table  — Excel 4-onglets Avicenna-compatible
                                    # (nécessite `pip install openpyxl`)

   # Après chaque run CI qui produit `test-results.json` :
12. /doc-stdr-export                # STDR   — Test description + résultats par fonctionnalité
13. /doc-str-export                 # STR    — Synthèse pass/fail pour l'auto report

14. Revue RAQA, signature           # workflow Word / git commit signé
    + compléter les sections jaunes <mark>[TODO ...]</mark> dans les .docx
    + compléter manuellement §2.9 Adequacy of Device Safety et §4.3 Benefit/Risk Analysis
    + signer le RISK-PLAN (méthodologie QMS) hors du plugin
```

**Étapes 2 et 4 ne sont JAMAIS automatisables** — elles capturent le
QMS-side context (intended use, signataires, references du dossier
technique) qui doit venir du système qualité, pas du code. Le plugin
les attend mais ne tente pas de les inférer.

## Stratégie hybride `external_resources` + yellow TODO

Pour chaque section narrative (architecture générale, intended use,
class diagram, COTS control, etc.), les commandes `/doc-*-export`
appliquent une **résolution en 3 étapes** :

1. **`dt-config.yaml: external_resources.<anchor>`** pointe vers un
   fichier → inliné verbatim (utile pour pointer une note Obsidian
   QMS, un Mermaid externe, un SBOM exporté…).
2. **`docs/dt-clinical-context.md`** a une section `## <anchor>` →
   inlinée.
3. Aucun des deux → **TODO surligné jaune** via `<mark>...</mark>`,
   rendu par pandoc en surbrillance Word avec un hint pour l'auteur QMS.

Exemple `dt-config.yaml` :
```yaml
external_resources:
  general-system-architecture: docs/qms/system-architecture.md
  class-diagram: docs/qms/diagrams/class-diagram.md
```

Tous les `<mark>[TODO ...]</mark>` restants apparaissent en **fond
jaune dans le `.docx`** sans aucune config pandoc supplémentaire —
l'auteur RAQA voit instantanément ce qui reste à remplir.

## Format d'ID configurable

Le format d'ID est lu depuis `dt-config.yaml: id_format`. Par défaut,
chaque writer mint des IDs en 3 segments :

```
SRS-AUTH-001    SDS-API-014    TC-PAY-003
```

Pour un format Avicenna-style 5-segments :

```yaml
# dt-config.yaml
product:
  suite: CINA
  application: CSP
id_format:
  default: "{CAT}-{SUITE}-{APP}-{DOMAIN}-{NNN:03d}"
```

Produit : `SRS-CINA-CSP-ACQ-020`, `SDS-CINA-CSP-NET-010`, etc.

**Variables disponibles** : `{CAT}`, `{SUITE}`, `{APP}`, `{DOMAIN}`,
`{NNN:03d}`. Per-category override possible (ex. `MAP: "..."`). Les
IDs existants ne sont JAMAIS reformatés — seuls les nouveaux IDs
suivent le format courant.

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

Tous les scripts `build_*.py` supportent `--strict` (exit ≠ 0 en cas de
défaut). Workflow CI typique :

```yaml
- run: python tools/build_docs.py --strict           # agrégats internes
- run: python tools/build_srs_export.py --strict     # SRS deliverable
- run: python tools/build_sdd_export.py --strict     # SDD
- run: python tools/build_stp_export.py --strict     # STP
- run: python tools/build_risk_export.py --strict    # Risk Report (.md + .csv)
- run: python tools/build_risk_xlsx.py --strict      # Risk Table (xlsx)

# Après l'exécution de la suite de tests :
- run: pytest --junit-xml=junit.xml ...
- run: <convert junit.xml → test-results.json schema>  # cf. test-results.example.json
- run: python tools/build_stdr_export.py --strict    # STDR (description + résultats)
- run: python tools/build_str_export.py --strict     # STR  (synthèse pass/fail)
```

`--strict` échoue sur :

- `build_docs.py` : marqueurs `[TODO]` / `[GAP-62304]` / `[GAP-CYBER]` /
  `[GAP-USE]` ; RSK ou THR ou URSK avec `severity: Critical` /
  `Catastrophic` (Classe A invalide) ou `residual_acceptable: false`.
- `build_*_export.py` (SRS/SDD/STP/STDR/STR) : tout `<mark>[TODO ...]</mark>`
  restant dans le rendu — utile pour gater la submission RAQA.
- `build_risk_export.py` : tout RSK / PRSK / THR avec
  `residual_acceptable: false`.
- `build_risk_xlsx.py` : tout risque avec `residual_acceptable: false`
  (cellule surlignée rouge).
- `build_stdr_export.py` / `build_str_export.py` : tout TC en statut
  `failed` dans `test-results.json`.

## Limites connues

- **IEC 62304 Classe A uniquement.** Pour B/C, dériver un skill
  `iec62304-class-b` et étendre les agents (intégration §5.6, gestion
  plus stricte des SOUP).
- **Pas de génération de diagrammes** (UML class diagram, workflow
  diagram). L'utilisateur peut pointer un fichier externe via
  `external_resources.class-diagram` (Mermaid, PlantUML, .png) ou
  laisser le yellow TODO pour intégration manuelle.
- **Benefit-risk analysis** (ISO 14971 §8) : explicitement
  non-générable. Les sections §2.9 du Risk Report et §4.3 Conclusion
  restent en yellow TODO — jugement humain RAQA obligatoire.
- **Le `risk-analyst` infère les hazards depuis le code** ; les hazards
  d'usage clinique purs (Intended Use, contre-indications) restent à
  apporter par le système qualité via `dt-clinical-context.md`.
- **Le `security-analyst` ne lance pas de scan actif.** Si un rapport
  `npm audit` / `pip-audit` / Snyk est fourni, il l'ingère ; sinon il
  recommande l'audit sans inventer de CVE.
- **`test-results.json` non auto-généré.** Le format est documenté dans
  `scaffold/test-results.example.json` ; la conversion `junit.xml` →
  `test-results.json` reste à brancher dans le pipeline CI du produit.
