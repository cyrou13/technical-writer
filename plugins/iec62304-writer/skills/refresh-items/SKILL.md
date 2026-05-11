---
name: refresh-items
description: Ajoute les champs frontmatter manquants à des items existants après une évolution du schéma (RSK étendu ISO 14971 §C.2 / §7.2 / §7.4 / §7.5 / §7.6, THR étendu CIA triad IEC 81001-5-1, etc.). Mode additif strict — n'écrase JAMAIS le contenu existant ni le corps Markdown.
---

## OUTPUT LANGUAGE — STRICT

Any artifact produced while applying this skill (the refresh report,
the inserted `[TODO]` placeholders, the audit log) MUST be written in
**English**, regardless of the user's conversational language or any
global `CLAUDE.md` instruction.

# Refresh items — additive schema migration

Ce skill comble le **gap mécanique** détecté par `/doc-migrate` §C :
les items existants dont le frontmatter manque les champs ajoutés par
une version récente du plugin.

## Pourquoi un skill séparé de `/doc-migrate`

`/doc-migrate` est un **audit read-only** par design — il ne touche
**jamais** au contenu utilisateur (cf. note `> Section C is read-only`).
C'est la bonne politique en medtech : modifier un item signé/approuvé
sans piste d'audit serait inacceptable.

`refresh-items` ouvre une voie automatique **mais conservatrice** :

- Mode `--dry-run` par défaut (audit identique à §C de `/doc-migrate`).
- Mode `--apply` : ajoute les champs manquants comme `[TODO]`
  placeholders (avec les valeurs par défaut du template courant comme
  starting points pour les enums).
- **Ne modifie jamais** le contenu existant : titles, hazards,
  severities, links, source, body Markdown.
- Bump `version` patch automatique (1.2.0 → 1.2.1) pour tracer la modif.
- `status: Approved → Draft` automatique pour forcer une re-approbation.
- Rapport groupé par signature de champs manquants (compact).

## Inputs

| Source | Obligatoire | Comportement |
|---|---|---|
| `docs/items/<CAT>/*.md` | oui | Items à refresh |
| Templates courants | oui | Résolution via `CLAUDE_PLUGIN_ROOT/scaffold/docs/templates/` en priorité (toujours à jour), fallback sur `docs/templates/` local. |

## Outputs

| Fichier | Mode | Contenu |
|---|---|---|
| `docs/generated/refresh-report.md` | toujours | Groupé par catégorie + signature de champs manquants |
| Items in-place | `--apply` seulement | Champs ajoutés à la fin du frontmatter, séparés des champs existants |

## CLI

```bash
python tools/refresh_items.py            # dry-run (audit only)
python tools/refresh_items.py --apply    # apply changes in-place
python tools/refresh_items.py --cat RSK  # limit to one category
python tools/refresh_items.py --stdout   # report to stdout
```

## Logique d'insertion

Pour chaque champ manquant du template courant :

1. Si le template a une **valeur scalar simple** (ex. `severity: Negligible`) →
   inséré tel quel (l'utilisateur voit un default sain à modifier).
2. Si le template a un **block scalar `|`** avec `[TODO ...]` interne (ex.
   `initiating_causes:`, `foreseeable_sequence:`) → inséré verbatim avec
   les `[TODO]` du template.
3. Si le template a une **enum value** (ex. `control_hierarchy: inherent_design`) →
   inséré comme starting point.
4. Si le template a une **liste vide** ou **null** → considéré comme
   OPTIONNEL et NON inséré (cohérent avec la logique anti-faux-positifs
   de `/doc-migrate`).

## Garde-fous

- **Ne touche jamais au contenu existant** : keys déjà présentes
  conservées, body Markdown inchangé.
- **Version bump + Draft reset** : tout item modifié devient une
  nouvelle version à re-approuver. Garantit la piste d'audit.
- **Pas de bulk-apply silencieux** : `--dry-run` par défaut.
  L'utilisateur doit explicitement `--apply` après avoir lu le rapport.
- **Pas d'inférence de contenu** : ce skill ne tente JAMAIS de "deviner"
  des valeurs cliniques (ex. `initiating_causes` d'un RSK). Tout reste
  en `[TODO]` jusqu'à édition humaine ou invocation d'un agent (e.g.
  `@risk-analyst refresh <ID>` pour un refresh sémantique guidé).

## Workflow type post-upgrade plugin

```bash
/plugin update iec62304-writer
/iec62304-writer:doc-init --update              # refresh scripts
/iec62304-writer:doc-migrate                    # voir ce qui manque
/iec62304-writer:doc-migrate --apply            # patch dt-config + clinical
/iec62304-writer:doc-refresh-items              # voir §C en bulk
/iec62304-writer:doc-refresh-items --apply      # appliquer additivement
# → reviewer chaque [TODO] inséré dans les items modifiés
# → ré-approuver (status: Draft → Approved) après review
/iec62304-writer:doc-build                      # vérifier que tout passe
```
