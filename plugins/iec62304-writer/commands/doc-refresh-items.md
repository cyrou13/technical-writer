---
description: Ajoute les champs frontmatter manquants à des items existants après upgrade du schéma (RSK étendu ISO 14971 §C.2, THR étendu CIA triad, etc.). Mode additif strict — ne touche jamais au contenu existant. Mode dry-run par défaut, --apply pour exécuter.
---

## OUTPUT LANGUAGE — STRICT

All artifacts produced by this command (refresh report, inserted
placeholders) MUST be written in **English**.

## Vérifications préalables

```bash
if [ -d .claude-plugin ]; then
  echo "ERROR: current directory is the plugin itself. Run from the TARGET repo." >&2
  exit 1
fi

if [ ! -d docs/items ]; then
  echo "ERROR: docs/items/ does not exist. Run /doc-init first." >&2
  exit 1
fi

if [ ! -f tools/refresh_items.py ]; then
  echo "INFO: tools/refresh_items.py not found — running from plugin scaffold."
fi
```

## Exécution

```bash
# Prefer the in-repo copy if present (scaffolded by /doc-init).
# Otherwise fall back to the plugin scaffold directly.
if [ -f tools/refresh_items.py ]; then
  CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT}" python tools/refresh_items.py $ARGUMENTS
else
  CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT}" python "${CLAUDE_PLUGIN_ROOT}/scaffold/tools/refresh_items.py" $ARGUMENTS
fi
```

## Synthèse à l'utilisateur (≤ 10 lignes)

Après l'exécution :

- Nombre d'items qui seraient/ont été modifiés
- Nombre total de champs ajoutés
- Par catégorie : nombre d'items × signature des champs manquants
- Chemin du rapport (`docs/generated/refresh-report.md`)
- Si dry-run : suggérer `/doc-refresh-items --apply` pour exécuter
- Si `--apply` : rappel que chaque item modifié est passé en `status: Draft`
  et version bumpée → à reviewer + ré-approuver

## Arguments

- `--apply` : exécute les modifications en place (sinon dry-run)
- `--cat <CAT>` : limite à une catégorie (RSK, THR, SDS, etc.)
- `--stdout` : rapport sur stdout au lieu de `docs/generated/refresh-report.md`
- `--auto-fill` : enchaîne 2 étapes —
  1. `refresh_items.py --apply` (insertion mécanique des `[TODO]`)
  2. invocation du sub-agent `items-refresher` qui REMPLIT
     sémantiquement les `[TODO]` (inférence depuis hazard / STRIDE / source).

  Implique `--apply`. À utiliser **uniquement après un dry-run validé**.
  Chaque item modifié reste en `status: Draft` — l'utilisateur reviewe
  le diff git item par item avant de re-approuver.

## Workflow `--auto-fill`

Quand `$ARGUMENTS` contient `--auto-fill` :

1. Vérifier qu'on a un repo avec items, un template à jour, etc.
2. Lancer `python tools/refresh_items.py --apply` pour insérer les `[TODO]`.
3. Lancer le sub-agent `items-refresher` (`Agent(subagent_type="items-refresher", ...)`)
   avec instruction de remplir les `[TODO]` restants en s'appuyant sur
   le hazard / STRIDE / source de chaque item.
4. Afficher le rapport final consolidé : combien de champs mécaniques
   ajoutés (étape 2) + combien de champs sémantiques remplis (étape 3)
   + items restant à reviewer à la main.

## Garde-fous

- **Ne touche JAMAIS** au contenu existant du frontmatter ou du body.
- **Bump version + reset status** automatiques sur chaque item modifié —
  l'item perd son `Approved` et doit être re-approuvé après review.
- **`[TODO]` placeholders** sur les nouveaux champs — l'utilisateur doit
  remplir manuellement ou via `@risk-analyst refresh <ID>` /
  `@security-analyst refresh <ID>` pour un refresh sémantique guidé.
- **Pas de commit/push automatique** — l'utilisateur valide via git
  diff avant de stage.
