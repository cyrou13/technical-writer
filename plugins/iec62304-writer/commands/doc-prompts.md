---
description: Génère des prompts ready-to-paste pour les SRS orphelins (sans SDS implémentant et/ou sans TC vérifiant). Un fichier prompt autonome par SRS sous `docs/generated/prompts/`, à coller dans une autre session Claude Code pour combler le gap. 3 types : impl, unit-tests, E2E Playwright (si UI).
---

## OUTPUT LANGUAGE — STRICT

All prompt files produced by this command MUST be in **English**
(target audience: Claude Code sessions, which perform best in English).

## Vérifications préalables

```bash
if [ -d .claude-plugin ]; then
  echo "ERROR: this directory is the plugin itself. Run from the TARGET repo." >&2
  exit 1
fi

if ! ls docs/items/SRS/*.md >/dev/null 2>&1; then
  echo "ERROR: no SRS items found. Run /doc-62304 first." >&2
  exit 1
fi
```

## Exécution

```bash
if [ -f tools/build_prompts.py ]; then
  python tools/build_prompts.py $ARGUMENTS
else
  echo "INFO: tools/build_prompts.py not found — running from plugin scaffold."
  CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT}" python "${CLAUDE_PLUGIN_ROOT}/scaffold/tools/build_prompts.py" $ARGUMENTS
fi
```

## Synthèse à l'utilisateur (≤ 10 lignes)

- Nombre de prompts générés (par type : impl / unit-tests / e2e)
- Chemin du catalogue : `docs/generated/prompts/_index.md`
- Workflow recommandé :
  - Ouvrir un prompt
  - Copier son contenu
  - Coller dans une nouvelle session Claude Code dans le repo cible
  - La session écrit le code + le test + l'item de doc + l'anchor
  - Commit, puis passer au prompt suivant
- Rappel : `--clean` pour nettoyer les prompts une fois les gaps comblés
  et la couverture revenue à 100%.

## Arguments

- `--cat impl|unit|e2e|all` : filtre par type de prompt (défaut `all`)
- `--srs <ID>` : un seul SRS (utile pour regen ciblé)
- `--clean` : supprime `docs/generated/prompts/*.md` avant de regénérer

## Garde-fous

- Ne touche JAMAIS aux items sous `docs/items/`.
- Régénère intégralement `docs/generated/prompts/` à chaque run.
- Ne lance JAMAIS les sessions Claude Code cibles — c'est à
  l'utilisateur de coller chaque prompt manuellement, item par item,
  pour garder le contrôle.
