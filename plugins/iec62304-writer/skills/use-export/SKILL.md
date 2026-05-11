---
name: use-export
description: Génère le triplet de livrables IEC 62366-1 — Usability Engineering File (UEF), Summative Evaluation (USE), et Annex 1 IECEE compliance checklist — à partir des items USC, URSK, SRS-USE-* et de `dt-config.yaml`. À invoquer pour produire `docs/export/<identifier>-UEF.md`, `docs/export/<identifier>-USE.md`, `docs/export/<identifier>-UEF-Annex1.md` (+ `.docx` optionnels) après que les items USC / URSK sont stables. Supporte deux modes : `platform-rich` (par défaut — tabulaire, multi-persona, scale SaaS) et `clinical-narrow` (narratif, 6 étapes linéaires, AI clinique étroit type CSpine).
---

## OUTPUT LANGUAGE — STRICT

Every artifact produced while applying this skill (the exported UEF
Markdown, the USE Markdown, the Annex 1 Markdown, the optional
`.docx` files produced via pandoc, all section headers and labels)
MUST be written in **English**, regardless of the user's
conversational language or any global `CLAUDE.md` instruction. The
framing sections come verbatim from `docs/dt-clinical-context.md`
and the static boilerplates under `docs/static/`, which are also
authored in English.

# Dossier technique — Usability Engineering File export

Ce skill produit le **triplet de livrables IEC 62366-1** attendu par
les RAQA medtech (Avicenna-style) à partir des items stockés sous
`docs/items/` et des métadonnées QMS-side capturées dans
`dt-config.yaml` + `docs/dt-clinical-context.md` + `docs/static/`.

## Pourquoi un livrable distinct de `70_usability_analysis.md`

`docs/generated/70_usability_analysis.md` (produit par `/doc-build`)
est un **agrégat technique** plat des items USC + URSK, optimisé
pour la revue de l'équipe dev. Le triplet d'export, lui, est un
ensemble de **documents QMS-ready** :

- page de garde signée (Written / Verified / Approved by) sur chacun,
- historique de révisions de chaque document,
- structure normative IEC 62366-1 :
  - **UEF** : Introduction → Use Specification → Risk Assessment →
    Formative Evaluations → Summative Evaluations (avec sample-size
    justification),
  - **USE** : Introduction → Summative Protocol → Summative Report →
    Annex A questionnaire,
  - **UEF-Annex1** : checklist IECEE clause-par-clause IEC 62366-1.

Le triplet est ce qu'on **envoie au notified body** ;
`70_usability_analysis.md` est ce qu'on **regarde en daily**.

## Inputs requis

| Input | Source | Obligatoire | Si absent |
|---|---|---|---|
| Items USC | `docs/items/USC/*.md` | oui | erreur |
| Items URSK | `docs/items/URSK/*.md` | non | §3.2 vide + warning |
| Items SRS-USE-* | `docs/items/SRS/*.md` filtrés | non | §3.4 table sans mitigations |
| Items RSK | `docs/items/RSK/*.md` | non | §3.3 sans cross-ref hazardous situations |
| Config QMS | `dt-config.yaml` | non | valeurs par défaut + `[TODO]` |
| Sections narratives | `docs/dt-clinical-context.md` | non | sections vides + `[TODO]` |
| Boilerplate sample-size | `docs/static/sample-size-justification.md` | non | UEF §5.1 vide + warning |
| Boilerplate questionnaire | `docs/static/clinical-evidence-questionnaire.md` | non | USE Annex A vide + warning |
| Boilerplate IECEE checklist | `docs/static/iec62366-annex1-checklist.csv` | non | Annex 1 vide + warning |
| Template Word | `dt-config.yaml: rendering.reference_docx` | non | rendu .docx avec style pandoc par défaut |

## Outputs

| Fichier | Format | Toujours produit |
|---|---|---|
| `docs/export/<identifier-uef>-UEF.md` | Markdown standalone | oui |
| `docs/export/<identifier-uef>-UEF.docx` | Word | si pandoc installé |
| `docs/export/<identifier-use>-USE.md` | Markdown standalone | oui |
| `docs/export/<identifier-use>-USE.docx` | Word | si pandoc installé |
| `docs/export/<identifier-annex1>-UEF-Annex1.md` | Markdown standalone | oui |
| `docs/export/<identifier-annex1>-UEF-Annex1.docx` | Word | si pandoc installé |
| `docs/export/<identifier>-use-export.log` | rapport de génération | oui |

Les `<identifier-*>` sont résolus dans cet ordre :

1. `dt-config.yaml: usability.document.identifier_{uef,use,annex1}` si défini,
2. dérivé du global `document.identifier` en remplaçant le suffixe
   `-SRS` / `-SDD` par `-UEF` / `-USE` / `-UEF-Annex1`,
3. sinon `UNKNOWN-UEF`, `UNKNOWN-USE`, `UNKNOWN-UEF-Annex1`.

La `<version_label>` (V01, V02, …) est appendée automatiquement
depuis `usability.document.version_label` (fallback :
`document.version_label`).

## Structure du livrable UEF (mode `platform-rich`)

```
COVER + Signatures + Revision history + TOC                  (auto)

§1 Introduction
   §1.1 Document overview                                     ← clinical-context: document-overview
   §1.2 Abbreviations and Glossary                            ← clinical-context: abbreviations + glossary
   §1.3 References (project + standard)                       ← dt-config.yaml: project_references
   §1.4 Conventions                                           ← auto from id_format

§2 Use Specification                                          (IEC 62366-1 §5.1)
   §2.1 Intended use                                          ← clinical-context: intended-use
   §2.2 Equipment application specification
       §2.2.1 Medical purpose                                 ← clinical-context: medical-purpose
       §2.2.2 Patient population                              ← clinical-context: patient-population
       §2.2.3 Intended user                                   ← clinical-context: end-users
       §2.2.4 Application / use environment                   ← clinical-context: application-environment
       §2.2.5 Resource requirements                           ← clinical-context: resource-requirements

§3 Risk assessment                                            (IEC 62366-1 §5.2-§5.6)
   §3.1 Characteristics related to safety
       §3.1.1 Primary operating functions and use scenarios   ← Table: Persona × Workflow × Linked USCs
                                                                Built from docs/items/USC/*.md grouped by `persona`
       §3.1.2 Reasonably foreseeable use errors                ← Table: UI surface × Failure mode × Linked URSKs
                                                                Built from docs/items/URSK/*.md grouped by `source`
   §3.2 Hazardous situations and hazard-related use scenarios ← Table: URSK ID × hazard × harm × severity × likelihood
                                                                Built from URSK items where risk_level ≠ Low
                                                                Cross-ref to docs/items/RSK/*.md sheet "Usability"
   §3.3 Hazard-related use scenarios for summative evaluation ← List of URSKs flagged with `summative: true`,
                                                                or [TODO summative-selection-rationale] if none flagged
   §3.4 Mitigation actions and user interface specification    ← Table: URSK ID × Mitigation SRS × TC verifying
                                                                Built from SRS items where links.mitigates ∋ URSK ID

§4 Formative Evaluations                                       ← <mark>[TODO formative-history]</mark>
   (Narrative — captures pre-summative user studies, beta programs,
   review sessions. By essence QMS-side, not derivable from code.)

§5 Summative Evaluations                                       (IEC 62366-1 §5.7-§5.9)
   §5.1 Sample size for usability testing                      ← static: sample-size-justification.md
   §5.2 Summative Evaluation Protocol                          ← cross-ref to USE deliverable §2
   §5.3 Summative Evaluation Report                            ← cross-ref to USE deliverable §3
```

## Structure du livrable UEF (mode `clinical-narrow`)

Identique au mode `platform-rich`, sauf §3.1.1 et §3.1.2 qui sont
**narratifs** (pas tabulaires) :

```
§3.1.1 Primary operating functions and use scenarios
       (Narrative — bullets a/b/c/d/e/f mirroring the Avicenna
        CSpine UEF style. Built from the union of USC bodies,
        flattened into 6-10 steps. Recommended only if count(USC)
        ≤ 10 AND count(distinct USC.persona) == 1.)

§3.1.2 Reasonably foreseeable use errors
       (Narrative — short prose enumerating the URSK use errors
        without grouping by surface.)
```

## Structure du livrable USE

```
COVER + Signatures + Revision history + TOC                  (auto)

§1 Introduction
   §1.1 Document overview                                     ← clinical-context: document-overview (or default narrative)
   §1.2 Abbreviations                                         ← clinical-context: abbreviations
   §1.3 Glossary                                              ← clinical-context: glossary
   §1.4 References                                            ← dt-config.yaml: project_references
   §1.5 Conventions                                           ← auto

§2 Summative Evaluation Protocol                              (IEC 62366-1 §5.7)
   §2.1 Conditions of tests                                   ← <mark>[TODO test-conditions]</mark> hint
   §2.2 Test scenarios                                        ← Auto from USC items: bullet list of normal usage sequences
                                                                Each scenario = USC.id + USC.title + numbered steps
   §2.3 Evaluation form                                       ← Reference to Annex A
   §2.4 Evaluation criteria                                   ← <mark>[TODO summative-criteria]</mark> hint
                                                                (e.g. "All N users answer YES to all scenarios")

§3 Summative Evaluation Report                                (IEC 62366-1 §5.9)
   §3.1 Overview of summative evaluation                      ← <mark>[TODO summative-overview]</mark>
   §3.2 Test results                                          ← <mark>[TODO summative-results]</mark>
   §3.3 Conclusion                                            ← <mark>[TODO summative-conclusion]</mark>

ANNEX A — Clinical Evidence Questionnaire                    ← static: clinical-evidence-questionnaire.md
                                                                with {DEVICE_NAME}, {DEVICE_VERSION},
                                                                {CONTACT_NAME}, {CONTACT_ROLE}, {CONTACT_EMAIL}
                                                                placeholders substituted from dt-config.yaml
```

## Structure du livrable UEF-Annex1

```
COVER (compact — single signatures block matching IECEE format)

Table 1 — Identification                                      (auto from dt-config.yaml)
Table 2 — IEC 62366-1 clauses 4 (General requirements)        ← static: iec62366-annex1-checklist.csv (rows where clause starts with "4")
Table 3 — IEC 62366-1 clauses 5 (Usability Engineering Process) ← static: iec62366-annex1-checklist.csv (rows where clause starts with "5")

Each row: Clause | Requirement | Result / Remark | Verdict (P/F/NA)

Placeholders {UEF_REF}, {USE_REF}, {SRS_REF}, {RISK_REPORT_REF}
substituted at build time from the resolved identifiers.
```

## Règles d'omission

- Item USC avec `status: Deprecated` → **exclu** du corps mais logge un warning.
- Item URSK avec `status: Deprecated` → exclu de §3.2 et §3.4.
- Section `## X` absente de `dt-clinical-context.md` → l'export
  insère `<mark>[TODO X]</mark>` (yellow highlight) à sa place et
  logge un warning.
- Boilerplate statique absent sous `docs/static/` → fallback sur
  `${CLAUDE_PLUGIN_ROOT}/scaffold/static/` ; si même absent là →
  insertion d'un `<mark>[TODO ...]</mark>` et log warning.

## Choix automatique du template

Si `dt-config.yaml: usability.template` est absent, le script peut
inférer :

- `count(USC) ≤ 10` ET `count(distinct USC.persona) ≤ 1` → suggère
  `clinical-narrow` en log (sans changer le mode — pour rester
  explicite, on garde `platform-rich` par défaut).
- Sinon → `platform-rich`.

Le log inclut toujours la phrase :

> Selected template: `platform-rich` (override via `usability.template` in dt-config.yaml).

## Rendu .docx (optionnel)

Si `dt-config.yaml: rendering.reference_docx` est défini ET pandoc
est installé :

```bash
pandoc docs/export/<id>-UEF.md \
  --reference-doc=<reference_docx> \
  --toc --toc-depth=3 \
  -o docs/export/<id>-UEF.docx
```

Idem pour USE et UEF-Annex1. Si pandoc absent → produire les `.md`
seulement et logger un warning non-bloquant. **Ne jamais** échouer
l'export pour absence de pandoc.

## Garde-fous

- L'export **ne modifie aucun item** sous `docs/items/`. Lecture seule.
- L'export **ne touche pas** `docs/generated/` (sortie de `/doc-build`).
- L'export **ne touche pas** `docs/static/` (boilerplate maintenu à la main).
- L'export écrit **uniquement** dans `docs/export/`.
- Idempotent : ré-exécuter `/doc-use-export` deux fois de suite avec des
  items inchangés produit les mêmes fichiers byte-pour-byte (sauf la date
  de génération si présente dans le rendu — préférer une date stable
  depuis `dt-config.yaml: usability.document.date`).
