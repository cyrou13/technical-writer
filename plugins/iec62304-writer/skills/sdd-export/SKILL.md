---
name: sdd-export
description: Génère le livrable Software Design Description (équivalent du Avicenna `AV-DP-CINA-CSP-10-007-SDD.docx`) — cover signataires, intro, architecture générale, application architecture (rationale + workflows + main software items + software units + class diagram), Security Risk Assessment (depuis THR), et COTS Control. À invoquer pour produire `docs/export/<identifier>-<vXX>-SDD.md` (+ `.docx` optionnel).
---

## OUTPUT LANGUAGE — STRICT

Every artifact produced while applying this skill (the exported SDD
Markdown, the optional `.docx`) MUST be written in **English**,
regardless of the user's conversational language or any global
`CLAUDE.md` instruction.

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
  - §3.6 Decomposition diagram, generated from the SDS `links.parent`:
    one level under one root → `flowchart TB`, the items in rows of 5
    (`DECOMPOSITION_ROW_ITEMS`) ranked by invisible `~~~` links so the
    figure is wider than tall; a deeper tree → `flowchart LR`. The
    optional `class-diagram` anchor follows it when written.
  - §3.7 Application Specific Design (détail SDS items)
- §4 Security Risk Assessment (depuis THR items, table d'attack
  paths, threat-by-threat, conclusion auto)
- §5 COTS Control and Identification (auto-detect des manifestes
  `pyproject.toml` / `requirements.txt` / `package.json`); §5.3 from
  `docs/ots.yaml: hazard_contribution` (below), else the `cots-hazards`
  anchor

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

## §5.3 Contribution to hazardous situations

`docs/ots.yaml: hazard_contribution` is written in the structured form and
rendered (`_lib.render_hazard_contribution`) as the `intro` sentence, a
three-column table `Contribution | Components | Containment` with one row per
entry of `ways` (`failure`, `components`, `containment`), then the `note`.
Free text is still accepted and printed as written; a value still carrying
`[TODO` falls back to the `cots-hazards` anchor.

```yaml
hazard_contribution:
  intro: Off-the-shelf software can contribute to a hazardous situation in three ways, each with a stated containment.
  ways:
    - failure: Wrong numeric result
      components: the numerical libraries and the inference runtime, on the path of every output value
      containment: pinned versions; accuracy test (SRS-…); release benchmark gate against a versioned baseline
  note: Components on no device code path cannot alter a result; their only failure mode is an import error.
```

### Diagrammes mermaid

Les blocs ```` ```mermaid ```` du livrable sont rendus en PNG et remplacés par
des images dans une **copie** du markdown que seul pandoc voit ; le `.md` livré
garde ses blocs mermaid. Sans ce rendu, pandoc recopie la source du diagramme
dans le `.docx` comme un bloc de code monospace — le relecteur lit
`participant P as Pipeline` en Courier au lieu d'un schéma.

Prérequis : `mermaid-cli` (`npm i -g @mermaid-js/mermaid-cli`). Variables
d'environnement reconnues :

| Variable | Rôle |
|---|---|
| `MMDC` | chemin du binaire `mmdc` si absent du `PATH` |
| `MERMAID_PUPPETEER_CONFIG` | config puppeteer JSON — typiquement `{"args": ["--no-sandbox"]}` en conteneur ; à défaut `tools/puppeteer.json` est lu s'il existe |

A rendered diagram taller than the page once pandoc has fitted it to the text
width (16 cm) gets `{height=20cm}` (`_lib._figure_size`): pandoc shrinks a wide
image on its own, never a tall one.

Absent → les blocs restent tels quels, une ligne INFO est loggée et l'export
n'échoue pas. Un diagramme qui ne compile pas est laissé en bloc de code : il ne
coûte pas les autres.

### Découpage des tableaux larges

L'inventaire OTS porte douze informations par composant : il est rendu en quatre
tableaux (identification ; fonctions utilisées et vérification ; revue de risque ;
fin de vie, SBOM et note), chacun rappelant le nom du composant. De même §3.5.1
(items logiciels) est scindé en « quoi » et « où », et §3.8 sépare la valeur du
paramètre de sa traçabilité. Règle : au-delà de cinq ou six colonnes sur A4
portrait, découper — voir « Lisibilité des tableaux » dans le skill `srs-export`.

## Front matter, figures and references (house format)

Applied by the shared helpers of `_lib.py` (skill `dossier-altitude`, "House
format"): the cover ends on the signature grid table (role in bold, one row per
signatory, the function under the name, date and signature blank); the
revision history follows in the form | **Version:** | **Date:** | **Part(s):** |
**Reason:** | with no heading and no rule; no `---` line between chapters; bare
"$" escaped before pandoc; one caption "Figure N: title" per diagram, N counted
over the document; references renumbered from R1 in listing order, citations
rewritten with them.

§1.4 opens on the brand sentence, then the identifier convention of software items (SDS): the structure in bold derived from `id_format`, "Example:" with the first active identifier of the store and its title or objective, "Where:" with one line per field. The format string itself is never printed. §3.6 cites the decomposition figure by the number it is rendered with.

## Garde-fous

- L'export **ne modifie aucun item** sous `docs/items/`. Lecture seule.
- L'export **ne touche pas** `docs/generated/`.
- L'export écrit **uniquement** dans `docs/export/`.
- Mode `--strict` : exit 1 si un seul `[TODO]` reste dans le rendu
  (utile en CI avant submission RAQA).
