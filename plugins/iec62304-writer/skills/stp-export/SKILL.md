---
name: stp-export
description: Génère le livrable Software Test Plan (STP) habillé pour le dossier technique à partir des TC items et de `dt-config.yaml`. Produit `docs/export/<identifier>-STP.md` (+ `.docx` optionnel). À invoquer après que les items TC sont stables et que `/doc-build` a produit `coverage.json`.
---

## OUTPUT LANGUAGE — STRICT

Every artifact produced while applying this skill (the exported STP
Markdown, the optional `.docx` produced via pandoc, all section headers
and labels) MUST be written in **English**, regardless of the user's
conversational language or any global `CLAUDE.md` instruction.
The framing sections come verbatim from `docs/dt-clinical-context.md`
which is also authored in English.

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

# Software Test Plan — STP export

Ce skill produit un **livrable de plan de test** au format attendu par
les RAQA medtech (Avicenna-style, structure proche de
`AV-DP-CINA-CSP-10-008-STP-V03.docx`) à partir des items TC stockés
sous `docs/items/TC/` et des métadonnées QMS capturées dans
`dt-config.yaml` + `docs/dt-clinical-context.md`.

## Distinction STP vs STD

| | `30_STD.md` (Software Test Description) | STP export |
|---|---|---|
| Produit par | `/doc-build` (`build_docs.py`) | `/doc-stp-export` (`build_stp_export.py`) |
| Nature | Agrégat interne des TC | **Plan** QMS-ready envoyé au notified body |
| Public | Équipe dev, revue technique | RAQA, auditeur, notified body |
| Contient | Tous les TC en détail | Structure normative STP (§1–§6) + table planned tests |
| Cover / signatures | Non | Oui |
| Sections narratives QMS | Non | Oui (via clinical-context) |

`30_STD.md` est ce qu'on **regarde en daily** ; le STP export est ce
qu'on **envoie au notified body** (ou qu'on joint au dossier technique).

## Chaîne de fallback pour les sections narratives

Pour chaque section narrative (§2.1, §3.1, §5, §6…), le script résout
l'ancre dans l'ordre suivant :

1. **`dt-config.yaml: external_resources.<anchor>`** — pointe vers un
   fichier Markdown externe (chemin relatif au repo). Contenu inliné
   verbatim. Priorité maximale.
2. **`docs/dt-clinical-context.md: ## <anchor>`** — section présente et
   non vide dans le fichier de contexte clinique.
3. **Yellow TODO fallback** — `<mark>[TODO anchor] hint</mark>` inséré
   dans le Markdown (converti en surlignage jaune Word par pandoc). En
   mode `--strict` : exit 1 si des markers sont présents.

## Anchors consommées

Les anchors suivantes sont lues depuis `dt-clinical-context.md` (ou
`external_resources`). Elles étendent les anchors déjà définies par
`/doc-srs-export` (SRS) et `/doc-risk-export` (Risk Report) :

| Anchor | Section STP | Description attendue |
|---|---|---|
| `test-environment-overview` | §2.1 + §1.1 | Processus de test : étapes cycle de vie, decision gates, distribution des rapports |
| `tests-schedule-logic` | §2.1.1 | Calendrier des tests : pre-commit, CI, nightly, pre-release |
| `test-tools` | §2.2.1 | Plateformes HW et outils SW de test |
| `test-data-doc` | §2.2.2 | Sources de données de test et gouvernance |
| `test-other-materials` | §2.2.3 | Autres matériaux : mocks, fixtures, DICOM samples |
| `test-installation` | §2.2.4 | Installation et maintenance de l'environnement de test |
| `personnel-and-training` | §2.2.5 | (existant — rôles et formation requis pour l'exécution des tests) |
| `tests-identification-strategy` | §3.1 | Stratégie d'identification des TC : depuis SRS, risks, use scenarios |
| `data-recording` | §3.4 | Enregistrement, post-processing (junit.xml, coverage) et analyse |
| `tests-schedule` | §5 | Calendrier planifié avec dates et jalons |
| `qualification` | §6 | Qualification plateforme et personnel |

Anchors héritées (partagées avec `/doc-srs-export`) :
`abbreviations`, `glossary`, `personnel-and-training`.

## Inputs requis

| Input | Source | Obligatoire | Si absent |
|---|---|---|---|
| Items TC | `docs/items/TC/*.md` | **oui** | erreur exit 1 |
| Items SRS | `docs/items/SRS/*.md` | non | §4.1.1 incomplet |
| Config QMS | `dt-config.yaml` | non | valeurs par défaut + `[TODO]` |
| Sections narratives | `docs/dt-clinical-context.md` | non | sections vides + yellow TODO |
| Coverage | `docs/generated/coverage.json` | non | §3.3 + §4.1.1 = yellow TODO |
| Template Word | `dt-config.yaml: rendering.reference_docx` | non | rendu .docx style pandoc par défaut |

## Outputs

| Fichier | Format | Toujours produit |
|---|---|---|
| `docs/export/<identifier>-<version>-STP.md` | Markdown standalone | oui |
| `docs/export/<identifier>-<version>-STP.docx` | Word | si pandoc installé |
| `docs/export/<identifier>-<version>-stp-export.log` | rapport de génération | oui |

### Règle de nommage de l'identifiant STP

- Si `dt-config.yaml: document.identifier` contient `SRS` → remplacer
  par `STP` (ex. `AV-DP-CINA-CSP-10-006-SRS` → `AV-DP-CINA-CSP-10-006-STP`).
- Sinon → appender `-STP` (ex. `AV-DP-CINA-CSP-10-008` → `AV-DP-CINA-CSP-10-008-STP`).

## Structure du livrable STP

```
COVER PAGE
  Title — Software Test Plan
  Identifier / version / date
  Signature table (grid: Written / Verified / Approved by, name + function, date, signature)

REVISION HISTORY TABLE

§1 INTRODUCTION
  §1.1 Document overview      ← test-environment-overview (or TODO)
  §1.2 Abbreviations & Glossary
  §1.3 Project References     ← dt-config.yaml: project_references
  §1.4 Conventions            ← brand sentence (product); identifier convention in §3.5

§2 TEST ENVIRONMENT
  §2.1 Test process           ← test-environment-overview
    §2.1.1 Tests schedule logic  ← tests-schedule-logic
  §2.2 Integration and factory test site
    §2.2.1 HW platform & SW tools ← test-tools
    §2.2.2 Test Data & doc        ← test-data-doc
    §2.2.3 Other test materials   ← test-other-materials
    §2.2.4 Installation & setup   ← test-installation
    §2.2.5 Personnel              ← personnel-and-training (existing anchor)

§3 TESTS IDENTIFICATION
  §3.1 Testing phases         ← tests-identification-strategy
  §3.2 Test progression       ← auto-narrative from TC type counts
  §3.3 Test coverage          ← from coverage.json (or TODO)
  §3.4 Data recording         ← data-recording
  §3.5 Test identification    ← auto-text from id_format

§4 PLANNED TESTS
  §4.1 Factory tests
    §4.1.1 Tests coverage     ← auto coverage table by SRS domain
    §4.1.2 Planned tests      ← table of all TC (sorted by ID, no Deprecated)
                                 | Identifier | Description | Requirement |

§5 TESTS SCHEDULE             ← tests-schedule (or TODO)

§6 QUALIFICATION              ← qualification (or TODO)
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

§1.4 is the brand sentence and a pointer to §3.5, which holds the identifier convention of test cases: the structure in bold derived from `id_format`, "Example:" with the first active identifier of the store and its title or objective, "Where:" with one line per field. The format string itself is never printed.

## Mode `--strict`

En mode `--strict`, le script échoue (exit 1) si le livrable généré
contient des marqueurs `<mark>[TODO ...]</mark>`. Utile en CI avant
soumission RAQA.

## Règles d'omission

- TC avec `status: Deprecated` → **exclu** de §4.1.2 (table planned tests).
- SRS avec `status: Deprecated` → exclu du calcul de couverture §4.1.1.
- Section absent de `dt-clinical-context.md` → yellow TODO marker.

## Garde-fous

- L'export **ne modifie aucun item** sous `docs/items/`. Lecture seule.
- L'export **ne touche pas** `docs/generated/` ni `30_STD.md`.
- L'export écrit **uniquement** dans `docs/export/`.
- **Ne jamais** commit ou push automatiquement — la sortie reste locale.
