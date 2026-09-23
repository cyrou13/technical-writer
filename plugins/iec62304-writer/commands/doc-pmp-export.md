---
description: Génère le Project Management Plan (PMP, …-10-001-PMP) selon les chapitres du PMP maison (CINA-CSpine / CINA-CTP) — équipe, WBS, planning et Gantt, fournisseurs, revues, gestion documentaire, cycle de vie, phases de test — à partir du bloc `project_management:` de `dt-config.yaml` et de `docs/dt-pmp-context.md`.
---

## OUTPUT LANGUAGE — STRICT

All artifacts written by this command (the exported PMP Markdown, the
optional `.docx`, the export log) MUST be written in **English**,
regardless of the user's conversational language or any global
`CLAUDE.md` instruction. Conversational replies MAY follow the user's
language; written outputs are English-only.

## What it runs

`python tools/build_pmp_export.py [--release | --internal] [--md-only]` at
the root of the target repository. `build_pmp_export.py` is a **reference
exporter**: it is not scaffolded, it is synced from the CINA-CTP repository
with `_lib.py` (see `tools/README.md`). If `tools/build_pmp_export.py` is
absent, say so and stop — do not write a PMP by hand.

## Where each part of the plan comes from

| PMP chapter | Source |
|---|---|
| Signature table | `document_approvals.pmp` over `approvals` — names only, one box per signatory (a role may be a list), date column blank |
| Revision history | `revision_history` |
| 1.1, 1.2, 1.4 | `docs/dt-pmp-context.md` (`document-overview`, `abbreviations`, `glossary`, `conventions`) |
| 1.3 Project References | `project_management.references` — a `document:` key takes number and title from `documents:` |
| 2.1 Team | `project_management.team` + `org_chart` |
| 2.2 WBS, tasks, planning | `task_types`, `wbs`, `planning` (periods, tool, target release) |
| 2.3 – 2.5 | context prose; 2.4.2 lists `suppliers` and cites `procedures.suppliers` |
| 3 Input data | derived: the PMAP, cited by its reference number |
| 4.2 Documentation | context prose + `procedures` + `documentation_tree` + the document numbering table derived from `documents:` (readiness review N11) |
| 5, 6 | context prose |
| 7 Problem resolution | `procedures.problem_resolution` |
| Annex A Planning | `planning.phases` / `milestones`: a Mermaid Gantt chart and the two tables — a dated record, exempt from the date-in-body rule |

`{PRODUCT}` in the context prose is replaced by `document.short_name`.

## Release gate

`--release` refuses the export (exit 2, offenders listed, nothing written)
while a `[TODO …]` marker remains — a WBS owner, a phase start, a supplier,
the tools list, the EU AI Act qualification. Dates outside Annex A are
refused. The team's names are the PMP's subject and are **not** register
offenders in this document (they are everywhere else).

## Checks before running

1. `dt-config.yaml` has `documents.pmp` and a `project_management:` block
   (scaffold: `/doc-init` writes a skeleton).
2. `docs/dt-pmp-context.md` exists (scaffold: the house prose, with
   `[TODO]` markers where the facts are project-specific).
3. The PMAP is numbered in `documents.pmap` if §3 is to cite it.

## Report

The path of the deliverable, the number of open markers, and — with
`--release` — the offenders by kind. Never fill a `[TODO]` with a guess:
the facts of a management plan (who, when, which supplier) come from the
project team.
