---
name: stdr-export
description: Génère le livrable STDR (Software Test Description and Reports — équivalent AV-DP-CINA-CSP-10-009-STDR) à partir des items TC/SRS, du fichier test-results.json émis par CI, et de dt-config.yaml. À invoquer pour produire docs/export/<identifier>-<vXX>-STDR.md (+ .docx optionnel) une fois les tests exécutés.
---

## OUTPUT LANGUAGE — STRICT

Every artifact produced while applying this skill (the STDR Markdown,
the optional `.docx`, the export log) MUST be written in **English**,
regardless of the user's conversational language or any global `CLAUDE.md`
instruction.

## Modes and release gate (contract of skill `submission-readiness`)

| Mode | Cover | Open points | `[TODO]` markers | Gate |
|---|---|---|---|---|
| (none) / `--strict` | `WORKING DRAFT — generated <date>` | omitted | yellow `<mark>` for the QMS author (`--strict` exits non-zero on any) | reported, never blocking |
| `--internal` | `WORKING DRAFT — generated <date>` | appended as a register | yellow `<mark>` | reported, never blocking |
| `--release` | document identifier (`documents.<x>`), version label, date and signatures from `dt-config.yaml` | never | refused | the gate of skill `submission-readiness` (DC-1…4, TL-1…14, SL-1…14) runs first; the export is **refused** and no file is written when any rule fails; DEC-1/2 are reported, never blocking |

`--release` and `--internal` are mutually exclusive. The rendering
follows the contract of skill `items-store`: internal sections
(`## Notes`, `## Open questions`, `## History`, a legacy
`## Changelog`) and HTML comments are stripped, each item is rendered
once, no per-item version is printed, and the unresolved-anomalies
appendix (a dated record) is exported in every mode while the
open-points register is `--internal` only. The scaffolded
`tools/build_*_export.py` are the working-draft generation and do not
implement `--release`; the reference exporters synced from the CINA-CTP
repository do (`tools/README.md`). Without them, `--release` states
that no deliverable can be produced.

# STDR — Software Test Description and Reports

## Distinction avec `30_STD.md`

`docs/generated/30_STD.md` (produit par `/doc-build`) est la **description
seule** des cas de test — il n'y a pas de résultats d'exécution.

Le livrable STDR (ce skill) est le **document QMS-ready** qui combine :
- la description (preconditions, steps, expected results),
- les résultats d'exécution réels (statuts CI, analyst, evidence, notes),
- la synthèse globale pass/fail par domain,
- les sections framing QMS (signataires, révisions, framing clinique).

C'est ce qu'on **envoie au notified body** ; `30_STD.md` est ce qu'on
**regarde en daily pour la couverture**.

## Inputs

| Source | Obligatoire | Si absent |
|---|---|---|
| `dt-config.yaml` | non | défauts + [TODO] |
| `docs/dt-clinical-context.md` | non | sections [TODO] yellow |
| `docs/items/TC/*.md` | oui | exit 1 |
| `docs/items/SRS/*.md` | non | grouping MISC au lieu du domain SRS |
| `test-results.json` (chemin configurable) | non | tous TC → `not_run` + TODO en tête §2 |

### Chemin du fichier test-results.json

Par défaut : `test-results.json` à la racine du repo cible.
Configurable via `dt-config.yaml`:
```yaml
test_results_path: test-results.json
```

### Format test-results.json

Défini dans `scaffold/test-results.example.json`. Champs principaux :
- `run_id`, `platform`, `git_sha`, `run_started`, `run_finished` — metadata du run.
- `results[]` — liste d'entrées avec `tc_id`, `status`, `duration_seconds`,
  `analyst`, `executed_at`, `evidence`, `notes`.

Statuts autorisés : `passed` | `failed` | `skipped` | `not_run` |
`manual_passed` | `manual_failed`.

### Chaîne de fallback pour les sections narratives

1. `dt-config.yaml: external_resources.<anchor>` pointe vers un fichier → inline.
2. `docs/dt-clinical-context.md` a une section `## <anchor>` → inline.
3. Aucun → marqueur yellow `<mark>[TODO ...]</mark>`.

Anchors consommés par ce livrable :
- `document-overview` → §1.1
- `abbreviations` → §1.2
- `test-preparation-data` → §3.1
- `test-preparation-environment` → §3.2
- `test-preparation-tools` → §3.3
- `rationale-for-decisions` → §5

## Structure du livrable

```
# <Title> — Software Test Description and Reports
(cover signataires)
(revision history)

# 1. Introduction
## 1.1 Document overview
## 1.2 Abbreviations and Glossary
## 1.3 Project References
## 1.4 Conventions

# 2. Overview of Test Results
## 2.1 Global summary (total/passed/failed/skipped/not_run)
## 2.2 Summary by test type (Unit/Integration/System/E2E)

# 3. Test Preparation
## 3.1 Data preparation
## 3.2 Environment preparation
## 3.3 Test tools

# 4. Detailed Test Description and Results
## 4.<k> <Domain>  (per SRS domain, sorted)
### <TC.id>
  Description, Verifies, Preconditions, Steps, Expected,
  Status, Analyst, Executed at, Evidence, Notes

# 5. Rationale for Decisions
```

## Front matter, figures and references (house format)

Applied by the shared helpers of `_lib.py` (skill `dossier-altitude`, "House
format"): the cover ends on the signature grid table (role in bold, one row per
signatory, the function under the name, date and signature blank); the
revision history follows in the form | **Version:** | **Date:** | **Part(s):** |
**Reason:** | with no heading and no rule; no `---` line between chapters; bare
"$" escaped before pandoc; one caption "Figure N: title" per diagram, N counted
over the document; references renumbered from R1 in listing order, citations
rewritten with them.

§1.4 opens on the brand sentence, then the identifier convention of test cases: the structure in bold derived from `id_format`, "Example:" with the first active identifier of the store and its title or objective, "Where:" with one line per field. The format string itself is never printed.

## Outputs

| Fichier | Format | Toujours produit |
|---|---|---|
| `docs/export/<id>-STDR-<v>-STDR.md` | Markdown | oui |
| `docs/export/<id>-STDR-<v>-STDR.docx` | Word | si pandoc + reference_docx |
| `docs/export/<id>-STDR-<v>-stdr-export.log` | log | oui |

L'identifier substitue `SRS` → `STDR` dans le `document.identifier`
de `dt-config.yaml`, ou appende `-STDR` si `SRS` absent.

## Garde-fous

- L'export ne modifie aucun item sous `docs/items/`. Lecture seule.
- L'export ne touche pas `docs/generated/`.
- L'export écrit uniquement dans `docs/export/`.
- Idempotent : ré-exécuter deux fois avec des inputs inchangés produit
  le même fichier.
- `--strict` exit 1 si [TODO] markers ou TC en `failed`.
