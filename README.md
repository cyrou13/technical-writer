# Technical writer — IEC 62304 Class A

Set d'agents, skills et workflows Claude Code pour générer la
documentation technique IEC 62304 (Classe A) à partir d'un codebase
TypeScript/JavaScript + Python — **sans dépendre d'un outil externe**
(reproduction locale des features utiles de Matrix Requirements).

## TL;DR

```bash
# Dans Claude Code, à la racine du projet à documenter :
/doc-62304            # pipeline complet
/doc-item SRS-AUTH-001 OAuth2 login    # créer/éditer un seul item
/doc-build            # ré-agréger les items en docs imprimables
```

Sortie : `docs/items/` (source de vérité, item-par-fichier) +
`docs/generated/` (agrégats SRS/SDS/Tests/Traçabilité).

## Architecture

### Skills (référentiels et règles)

| Skill | Rôle |
|---|---|
| `iec62304-class-a` | Livrables 62304 Classe A et leur contenu minimal |
| `items-store` | Convention de stockage local (item-par-fichier, IDs, liens) |
| `srs-extract` | Extraction d'exigences depuis le code |
| `sds-generate` | Extraction de design et architecture |
| `test-evidence` | Découverte des tests, formalisation en TC |
| `traceability-matrix` | Spec de la matrice de couverture |

### Sub-agents (un par étape lourde, contexte isolé)

| Agent | Rôle |
|---|---|
| `code-archeologist` | Cartographie du repo → `docs/generated/_codemap.md` |
| `requirements-writer` | Génère `docs/items/SRS/*.md` |
| `architecture-writer` | Génère `docs/items/SDS/*.md` |
| `test-evidence-collector` | Génère `docs/items/TC/*.md` |
| `compliance-reviewer` | Revue 62304 Classe A → `99_compliance_review.md` |

### Slash commands

| Commande | Effet |
|---|---|
| `/doc-62304 [scope]` | Pipeline complet (cartographie → rédaction → build → revue) |
| `/doc-item <ID> [titre]` | CRUD d'un item unique avec template |
| `/doc-build [--strict]` | Lance `tools/build_docs.py` |

## Reproduction des features Matrix Requirements

| Matrix Requirements | Équivalent local |
|---|---|
| Items à ID stable, catégories | `docs/items/<CAT>/<ID>.md` |
| Liens UP/DOWN, traçabilité N:N | `links:` en frontmatter YAML |
| Coverage views | `docs/generated/40_traceability.md` + `coverage.json` |
| Item revisions / audit log | git history + commits signés |
| Workflow review/approve | `status: Draft → Approved`, PR + reviewers |
| Export DOCX/PDF | `pandoc docs/generated/*.md -o doc.pdf` |
| Item DOORS-like editing | `/doc-item <ID>` |

## Structure du repo

```
.claude/
├── skills/
│   ├── iec62304-class-a/SKILL.md
│   ├── items-store/SKILL.md
│   ├── srs-extract/SKILL.md
│   ├── sds-generate/SKILL.md
│   ├── test-evidence/SKILL.md
│   └── traceability-matrix/SKILL.md
├── agents/
│   ├── code-archeologist.md
│   ├── requirements-writer.md
│   ├── architecture-writer.md
│   ├── test-evidence-collector.md
│   └── compliance-reviewer.md
└── commands/
    ├── doc-62304.md
    ├── doc-item.md
    └── doc-build.md
docs/
├── items/
│   ├── SRS/    # exigences logicielles
│   ├── SDS/    # design & architecture
│   └── TC/     # cas de test
├── templates/  # squelettes pour /doc-item
└── generated/  # produit par /doc-build (NE PAS éditer à la main)
tools/
└── build_docs.py    # agrégation + matrice de traçabilité
```

## Schéma d'un item

```yaml
---
id: SRS-AUTH-001
title: Authentification OAuth2
status: Draft           # Draft | Approved | Deprecated
version: 1.0.0
created: 2026-05-07
updated: 2026-05-07
verification: Test
priority: Must
source:
  - src/auth/oauth.ts
  - src/auth/oauth.test.ts
links:
  parent: []
  implements: []        # rempli sur les SDS
  verifies: []          # rempli sur les TC
  mitigates: []
---

## Description
Le système doit ...

## Critères d'acceptation
- [ ] ...
```

## Conventions clés

- **IDs immuables.** Une exigence retirée passe à `Deprecated`. Jamais
  renumérotée, jamais supprimée.
- **Pas d'invention.** Tout item doit être traçable à un fichier source.
  Sinon `[TODO]` explicite.
- **Idempotence.** Les agents préservent les IDs existants et bumpent
  `version` uniquement quand le contenu de fond change.
- **`docs/generated/` est régénérable.** Ne pas l'éditer à la main —
  toute modification doit passer par `docs/items/`.

## CI

Pour valider la doc en CI sans dépendance :

```yaml
- run: python tools/build_docs.py --strict
```

`--strict` échoue dès qu'un `[TODO]` ou `[GAP-62304]` traîne.

## Limites v1

- Classe A uniquement. Pour B/C, créer un skill `iec62304-class-b` et
  étendre les agents (intégration §5.6, gestion plus stricte des SOUP,
  risque détaillé §7).
- Pas d'export DOCX/PDF intégré — utiliser `pandoc` à la main si besoin
  d'un livrable réglementaire formaté.
- Pas de gestion des risques détaillée — la catégorie `RSK` est
  réservée mais pas peuplée par les agents v1.
- Le statut d'exécution des tests (`Passing`/`Failing`) n'est pas mis à
  jour automatiquement par défaut — fournir un rapport JUnit/pytest pour
  l'enrichir.
