---
name: str-export
description: Génère le livrable STR-auto (Software Test Report — automated, équivalent AV-DP-CINA-CSP-10-010-STR-auto) à partir du fichier test-results.json émis par CI et de dt-config.yaml. Format synthétique centré sur la vue pass/fail du run CI. À invoquer après chaque run CI significatif.
---

## OUTPUT LANGUAGE — STRICT

Every artifact produced while applying this skill (the STR Markdown,
the optional `.docx`, the export log) MUST be written in **English**,
regardless of the user's conversational language or any global `CLAUDE.md`
instruction.

# STR-auto — Software Test Report

## Distinction avec le STDR

| | STDR | STR-auto |
|---|---|---|
| Contenu | Description + résultats (TC complets) | Synthèse du run CI |
| TC requis | oui (exit 1 si absent) | non (TC optionnels pour titres) |
| test-results.json requis | non (fallback not_run) | non (fallback TODO) |
| Longueur typique | long (1 section par TC) | court (4 sections) |
| Audience | Notified body, RAQA | Équipe dev, QA daily |

## Inputs

| Source | Obligatoire | Si absent |
|---|---|---|
| `dt-config.yaml` | non | défauts + [TODO] |
| `docs/dt-clinical-context.md` | non | sections [TODO] yellow |
| `test-results.json` (chemin configurable) | non | §4 → TODO yellow |
| `docs/items/TC/*.md` | non | titres TC non résolus dans le détail |

### Chemin du fichier test-results.json

Par défaut : `test-results.json` à la racine du repo cible.
Configurable via `dt-config.yaml`:
```yaml
test_results_path: test-results.json
```

### Format test-results.json

Voir `scaffold/test-results.example.json`. Statuts autorisés : `passed` |
`failed` | `skipped` | `not_run` | `manual_passed` | `manual_failed`.

### Chaîne de fallback pour les sections narratives

1. `dt-config.yaml: external_resources.<anchor>` pointe vers un fichier → inline.
2. `docs/dt-clinical-context.md` a une section `## <anchor>` → inline.
3. Aucun → marqueur yellow `<mark>[TODO ...]</mark>`.

Anchors consommés par ce livrable :
- `document-overview` → §1.1
- `abbreviations` → §1.2
- `automated-tests-platform` → §2
- `local-tests-platforms` → §3

## Structure du livrable

```
# <Title> — Software Test Report (auto)
(cover signataires)
(revision history)

# 1. Introduction
## 1.1 Document overview
## 1.2 Abbreviations and Glossary
## 1.3 Project References
## 1.4 Conventions

# 2. Automated Tests Platform
  [automated-tests-platform anchor ou TODO]

# 3. Local Tests Platforms
  [local-tests-platforms anchor ou TODO]

# 4. Overview of Test Results
## 4.1 Run metadata (run_id, platform, git_sha, started/finished)
## 4.2 Synthesis table (total/passed/failed/skipped/not_run)
## 4.3 TC IDs by status (liste par statut)
## 4.4 Failed tests detail (TC ID, description, erreur, evidence)
```

Si `test-results.json` absent : §4 affiche un TODO yellow et une table vide.

## Outputs

| Fichier | Format | Toujours produit |
|---|---|---|
| `docs/export/<id>-STR-<v>-STR.md` | Markdown | oui |
| `docs/export/<id>-STR-<v>-STR.docx` | Word | si pandoc + reference_docx |
| `docs/export/<id>-STR-<v>-str-export.log` | log | oui |

L'identifier substitue `SRS` → `STR` dans le `document.identifier`
de `dt-config.yaml`, ou appende `-STR` si `SRS` absent.

## Garde-fous

- L'export ne modifie aucun item. Lecture seule.
- L'export écrit uniquement dans `docs/export/`.
- Idempotent.
- `--strict` exit 1 si [TODO] markers ou TC en `failed`.
