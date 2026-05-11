---
name: sdd-export
description: Génère le livrable Software Design Description (équivalent du Avicenna `AV-DP-CINA-CSP-10-007-SDD.docx`) — cover signataires, intro, architecture générale, application architecture (rationale + workflows + main software items + software units + class diagram), Security Risk Assessment (depuis THR), et COTS Control. À invoquer pour produire `docs/export/<identifier>-<vXX>-SDD.md` (+ `.docx` optionnel).
---

## OUTPUT LANGUAGE — STRICT

Every artifact produced while applying this skill (the exported SDD
Markdown, the optional `.docx`) MUST be written in **English**,
regardless of the user's conversational language or any global
`CLAUDE.md` instruction.

# Software Design Description — export

Ce skill produit un livrable **SDD** au format attendu par les RAQA
medtech (IEC 62304 §5.3-§5.4 design + IEC 81001-5-1 §security
assessment + AAMI TIR57 § COTS) à partir des items SDS / SRS / THR et
des métadonnées QMS dans `dt-config.yaml` + `docs/dt-clinical-context.md`.

## Pourquoi un livrable distinct de `20_SDS.md`

`docs/generated/20_SDS.md` est un **agrégat plat** des items SDS,
consommé en daily review. Le SDD est un **document QMS-ready** avec :

- page de garde signée (Written / Verified / Approved by)
- historique de révisions
- §2 General System Architecture (narratif QMS)
- §3 Application Architecture :
  - §3.1 Rationale for software architecture decisions (agrégé depuis
    les `## Design notes` des SDS)
  - §3.2 Hardware and Software Requirements (narratif)
  - §3.3 Processing Workflow + §3.4 Application Workflow (narratif)
  - §3.5 Software Design Description (Main items + Software Units +
    Error codes)
  - §3.6 Class Diagram (image / Mermaid externe)
  - §3.7 Application Specific Design (détail SDS items)
- §4 Security Risk Assessment (depuis THR items, table d'attack
  paths, threat-by-threat, conclusion auto)
- §5 COTS Control and Identification (auto-detect des manifestes
  `pyproject.toml` / `requirements.txt` / `package.json`)

## Inputs requis

| Input | Source | Obligatoire | Si absent |
|---|---|---|---|
| Items SDS | `docs/items/SDS/*.md` | oui | erreur |
| Items SRS | `docs/items/SRS/*.md` | non | §4.5 et §4.6 = `[TODO]` |
| Items THR | `docs/items/THR/*.md` | non | §4.2-4.3 = "no THR items" |
| Config QMS | `dt-config.yaml` | non | défauts + TODOs |
| Sections narratives | `docs/dt-clinical-context.md` | non | yellow TODOs |
| Manifestes deps | `pyproject.toml` / `requirements.txt` / `package.json` | non | §5.2 = TODO |
| Template Word | `dt-config.yaml: rendering.reference_docx` | non | rendu .docx style pandoc |

## Outputs

| Fichier | Format | Toujours produit |
|---|---|---|
| `docs/export/<id>-<v>-SDD.md` | Markdown | oui |
| `docs/export/<id>-<v>-SDD.docx` | Word | si pandoc + reference_docx |
| `docs/export/<id>-<v>-sdd-export.log` | log | oui |

## Chaîne de fallback pour sections narratives

Pour chaque section narrative (`general-system-architecture`,
`hardware-and-software-requirements`, `processing-workflow`,
`application-workflow`, `error-code-standardization`, `class-diagram`,
`cots-control`, `cots-hazards`, `penetration-testing`,
`security-objectives`, etc.), résolution en 3 étapes :

1. **`dt-config.yaml: external_resources.<anchor>`** pointe vers un
   fichier → inliné verbatim.
2. **`docs/dt-clinical-context.md`** a une section `## <anchor>` →
   inlinée.
3. Aucun des deux → **TODO surligné jaune** (HTML `<mark>` rendu par
   pandoc en Highlight Word) avec un hint pour l'auteur QMS.

## Auto-detect des dépendances COTS (§5.2)

Si l'un des manifestes suivants est présent à la racine du repo, ses
**dépendances directes** sont listées en table §5.2 :

- `pyproject.toml` (clé `dependencies` PEP 621)
- `requirements.txt` (lignes non commentées)
- `package.json` (`dependencies` + `devDependencies`)

Les dépendances **transitives** ne sont PAS listées — l'utilisateur
doit générer un SBOM complet via `syft` ou `cyclonedx` et référencer
le fichier dans §5.1 (via `external_resources.cots-control`).

## Garde-fous

- L'export **ne modifie aucun item** sous `docs/items/`. Lecture seule.
- L'export **ne touche pas** `docs/generated/`.
- L'export écrit **uniquement** dans `docs/export/`.
- Mode `--strict` : exit 1 si un seul `[TODO]` reste dans le rendu
  (utile en CI avant submission RAQA).
