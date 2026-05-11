---
name: risk-xlsx-export
description: Génère le livrable Excel 4-onglets (Design / Production / Usability / Cybersecurity) équivalent du fichier Avicenna `annex1-RISK-TABLE.xlsx` à partir des items RSK / PRSK / URSK / THR et de `dt-config.yaml`. À invoquer pour produire `docs/export/<identifier>-<vXX>-RISK-TABLE.xlsx` (nécessite `openpyxl`).
---

## OUTPUT LANGUAGE — STRICT

Every artifact produced while applying this skill (the .xlsx headers,
cell contents, sheet names, log) MUST be written in **English**,
regardless of the user's conversational language or any global
`CLAUDE.md` instruction.

# Risk inventory — Excel export

Ce skill produit un livrable **Excel à 4 onglets** matching le format
Avicenna `AV-DP-CINA-CSP-10-005-annex1-RISK-TABLE.xlsx`, à partir des
items stockés sous `docs/items/{RSK,PRSK,URSK,THR}/`.

## Pourquoi un .xlsx en plus du .md / .docx

| Format | Produit par | Usage |
|---|---|---|
| `50_risk_analysis.md` | `/doc-build` | Agrégat interne pour revue PR |
| `RISK-REPORT.md` + `.docx` | `/doc-risk-export` | Livrable narratif RAQA (ISO 14971 §B) |
| `RISK-TABLE.csv` | `/doc-risk-export` | Inventaire flat 18-colonnes |
| `RISK-TABLE.xlsx` | `/doc-risk-xlsx` | **Inventaire structuré 4-onglets** Avicenna-compatible |

Le .xlsx est l'**inventaire d'audit** : ce que le notified body lit
quand il veut vérifier ligne par ligne quelle classification a été
appliquée, quels contrôles formels mitigent chaque hazard, et quel
résiduel a été déclaré. C'est aussi le format **Matrix Requirements-like**
qui permet l'aller-retour avec un outil GRC externe.

## Dépendance openpyxl

Le script `tools/build_risk_xlsx.py` requiert le package Python
`openpyxl` (pas stdlib). Si absent, le script exit 1 avec un message
clair :

```
ERROR: openpyxl is required but not installed.
Install with:  pip install openpyxl
The CSV inventory produced by /doc-risk-export remains available as a fallback.
```

Installation typique :

```bash
pip install openpyxl
# ou via uv
uv pip install openpyxl
```

`openpyxl` est la seule dépendance non-stdlib du plugin — toutes les
autres commandes (`/doc-62304`, `/doc-build`, `/doc-export`,
`/doc-risk-export`) tournent en stdlib pure.

## Inputs

| Input | Source | Obligatoire | Si absent |
|---|---|---|---|
| Items RSK | `docs/items/RSK/*.md` | non | Onglet Design vide (headers seuls) |
| Items PRSK | `docs/items/PRSK/*.md` | non | Onglet Production vide |
| Items URSK | `docs/items/URSK/*.md` | non | Onglet Usability vide |
| Items THR | `docs/items/THR/*.md` | non | Onglet Cybersecurity vide |
| Items SRS/SDS/TC | `docs/items/*` | non | "Mitigating Items" reste vide par risque |
| Config QMS | `dt-config.yaml` | non | Filename "UNKNOWN-V01-RISK-TABLE.xlsx" |

Au moins **une** catégorie de risque doit être non vide, sinon le
script exit 1 avec un message d'erreur ("Run /doc-62304 first").

## Outputs

| Fichier | Format | Toujours produit (si openpyxl) |
|---|---|---|
| `docs/export/<id>-<v>-RISK-TABLE.xlsx` | Excel 4 sheets | oui |
| `docs/export/<id>-<v>-risk-xlsx.log` | log | oui |

## Structure des 4 onglets

### Onglet 1 — Design risk analysis (22 colonnes, RSK)

Risk ID · Software Function · Software Item · Hazard · Initiating causes · Foreseeable sequence · Hazardous situation · Harm · Initial Probability · Initial Severity · Initial Risk Index · Initial Risk Level · Initial Acceptable · Control Hierarchy · Mitigating Items · Residual Probability · Residual Severity · Residual Risk Index · Residual Risk Level · Residual Acceptable · Arising Risks · Labeling Disclosure

### Onglet 2 — Production risk analysis (20 colonnes, PRSK)

Risk ID · Production Phase · Asset at Risk · Hazard · Initiating causes · Foreseeable sequence · Hazardous situation · Harm · Initial Probability · Initial Severity · Initial Risk Index · Initial Risk Level · Initial Acceptable · Control Hierarchy · Mitigating Items · Residual Probability · Residual Severity · Residual Risk Index · Residual Risk Level · Residual Acceptable

### Onglet 3 — Usability risk analysis (16 colonnes, URSK)

Risk ID · Use Scenario (USC) · Use Error · Hazard · Hazardous Situation · Harm · Initial Likelihood · Initial Severity · Initial Risk Level · Initial Acceptable · Mitigating Items · Residual Likelihood · Residual Severity · Residual Risk Level · Residual Acceptable · Triggered RSK (cascade)

### Onglet 4 — Cybersecurity risk analysis (15 colonnes, THR avec CIA)

Risk ID · STRIDE · Attacker model · Asset · Vulnerability description · Initial — Confidentiality · Initial — Integrity · Initial — Availability · Mitigation / Remediation · Mitigating Items · Residual — Confidentiality · Residual — Integrity · Residual — Availability · Residual Acceptable · Triggered RSK (cascade)

Le format CIA reproduit exactement la structure du sheet Avicenna
"Cybersecurity risk analysis" (annex1 de `RISK-TABLE`), avec sévérité
par dimension `n/a | Low | Medium | High`.

## Formatage

- **Ligne 1 (headers)** : bold, fond gris (`#DDDDDD`), wrap text, hauteur 32 px, freeze pane après.
- **Cellules de risque résiduel non-acceptable** : fond rouge clair (`#FFCCCC`) sur la cellule
  "Residual Acceptable" — alerte visuelle immédiate.
- **Toutes les cellules** : wrap text + alignement top-left pour les blocs scalaires multilignes
  (`initiating_causes`, `foreseeable_sequence`).
- **Largeur des colonnes** : pré-réglée par colonne (ID = 16, texte court = 22, texte long = 40).

## Garde-fous

- L'export **ne modifie aucun item** sous `docs/items/`.
- L'export **ne touche pas** `docs/generated/` ni `docs/export/*RISK-REPORT*`.
- L'export écrit **uniquement** dans `docs/export/`.
- Idempotent : la re-génération produit le même fichier (sauf metadata
  date inhérente au format Excel — non comparable au binaire).
- Mode `--strict` : exit 1 si ≥ 1 risque a `residual_acceptable: False`.
