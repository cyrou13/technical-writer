---
name: risk-report-export
description: Génère le livrable Risk Analysis Report (équivalent annex2-RISK-REPORT.docx d'Avicenna) + une table d'inventaire CSV (équivalent simplifié annex1-RISK-TABLE.xlsx) à partir des items RSK / THR / URSK et de `dt-config.yaml`. À invoquer pour produire `docs/export/<identifier>-<vXX>-RISK-REPORT.md` (+ `.docx` optionnel) après que les items risques sont stables.
---

## OUTPUT LANGUAGE — STRICT

Every artifact produced while applying this skill (the exported Risk
Report Markdown, the CSV inventory, the optional `.docx`) MUST be
written in **English**, regardless of the user's conversational
language or any global `CLAUDE.md` instruction.

# Risk Analysis Report — export

Ce skill produit un livrable **Risk Analysis Report** au format attendu
par les RAQA medtech (ISO 14971:2019 §B + IEC 62304 §7 + IEC 81001-5-1)
à partir des items RSK / THR / URSK stockés sous `docs/items/` et des
métadonnées QMS de `dt-config.yaml` + `docs/dt-clinical-context.md`.

## Pourquoi un livrable distinct de `50_risk_analysis.md`

`docs/generated/50_risk_analysis.md` (produit par `/doc-build`) est
l'**agrégat interne** consommé par la revue de conformité et le
compliance-reviewer. Le livrable d'export est un **document QMS-ready** :

- page de garde signée (Written / Verified / Approved by),
- historique de révisions du document,
- §2.1-2.3 framing clinique (intended use, end users, characteristics
  affecting safety),
- §2.4 Risk Level Ranking (matrice acceptabilité),
- §2.5 Software safety classification (auto-justifiée Classe A vs B/C),
- §2.6 Détail par RSK avec **chaîne causale complète ISO 14971 §C.2**,
- §2.7 Generation of Other Hazards (cascade `arising_risks`),
- §2.8 Residual risk evaluation,
- §2.9 + §4.3 Benefit/Risk → **`[TODO]` bloquant** (jugement humain),
- §3 Cybersecurity (depuis items THR),
- §4 Conclusion.

C'est ce qu'on **envoie au notified body** ; `50_risk_analysis.md` est
ce qu'on **regarde en daily**.

## Inputs requis

| Input | Source | Obligatoire | Si absent |
|---|---|---|---|
| Items RSK | `docs/items/RSK/*.md` | oui | erreur (lancer `/doc-62304` d'abord) |
| Items THR | `docs/items/THR/*.md` | non | §3 Cyber design assessment vide |
| Items URSK | `docs/items/URSK/*.md` | non | absent du CSV d'inventaire |
| Items SRS/SDS/TC | `docs/items/*` | non | "Mitigating items" reste vide par RSK |
| Config QMS | `dt-config.yaml` | non | défauts + `[TODO]` |
| Sections narratives | `docs/dt-clinical-context.md` | non | sections vides + `[TODO]` |
| Template Word | `dt-config.yaml: rendering.reference_docx` | non | rendu `.docx` style pandoc défaut |

## Outputs

| Fichier | Format | Toujours produit |
|---|---|---|
| `docs/export/<id>-<v>-RISK-REPORT.md` | Markdown | oui |
| `docs/export/<id>-<v>-RISK-REPORT.docx` | Word | si pandoc + reference_docx |
| `docs/export/<id>-<v>-RISK-TABLE.csv` | CSV 18 colonnes | oui |
| `docs/export/<id>-<v>-risk-export.log` | log | oui |

## Anchors clinical-context.md additionnels

Ce livrable consomme **deux anchors** dans `docs/dt-clinical-context.md`
qui ne sont PAS utilisés par `/doc-export` (le livrable SRS) :

- `## end-users` → §2.2 du Risk Report
- `## characteristics-affecting-safety` → §2.3 du Risk Report

Si ces sections n'existent pas dans `dt-clinical-context.md`, le rendu
contient `[TODO end-users]` / `[TODO characteristics-affecting-safety]`.
L'utilisateur doit les ajouter à la main avant la submission RAQA.

## Software safety classification (auto-justifiée)

Le script vérifie si **aucun** RSK n'a `severity: Critical` ou
`Catastrophic` (initial OU residual). Si OK → §2.5 affirme
"IEC 62304 Class A — all hazards have severity ≤ Serious". Sinon →
flagge "⚠ Class B/C escalation required" et liste les RSK fautifs.

## §2.9 / §4.3 Benefit/Risk — NON auto-générable

Ces deux sections sont **explicitement** templatées avec `[TODO —
human judgement required]`. Elles capturent le jugement final
benefit/risk (ISO 14971 §8) qui ne peut être inféré du code. La
commande `/doc-risk-export --strict` échoue si ces sections restent en
`[TODO]` — la submission RAQA est invalide tant qu'un signataire
n'a pas complété.

## Garde-fous

- L'export **ne modifie aucun item** sous `docs/items/`. Lecture seule.
- L'export **ne touche pas** `docs/generated/`.
- L'export écrit **uniquement** dans `docs/export/`.
- Idempotent : ré-exécuter `/doc-risk-export` deux fois de suite avec
  des items inchangés produit le même fichier.
