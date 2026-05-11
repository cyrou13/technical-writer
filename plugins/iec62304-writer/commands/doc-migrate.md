---
description: Audit de migration pour un projet déjà initialisé avec une version antérieure du plugin. Détecte les clés manquantes dans dt-config.yaml, les anchors manquants dans dt-clinical-context.md, les items au frontmatter incomplet, et les scripts build_*.py manquants ou outdatés. Mode dry-run par défaut, --apply pour les changements additifs.
---

## OUTPUT LANGUAGE — STRICT

All artifacts produced by this command (migration report, inline messages)
MUST be written in **English**, regardless of the user's conversational
language or any global `CLAUDE.md` instruction.

## Vérifications préalables

```bash
# Ensure we are inside a target repo (not the plugin itself)
if [ -d .claude-plugin ]; then
  echo "ERROR: current directory is the plugin itself. Run /doc-migrate from the TARGET repo." >&2
  exit 1
fi

# Require at least one of the two sentinel files
if [ ! -f tools/build_docs.py ] && [ ! -f dt-config.yaml ]; then
  echo "ERROR: neither tools/build_docs.py nor dt-config.yaml found." >&2
  echo "  This does not look like a repo initialised with /doc-init." >&2
  echo "  Run /doc-init first, then /doc-migrate." >&2
  exit 1
fi

echo "Target repo: $(pwd)"
echo "Plugin root: ${CLAUDE_PLUGIN_ROOT}"
```

## Exécution

```bash
# build_migrate.py is scaffolded into the target repo by /doc-init
# CLAUDE_PLUGIN_ROOT is automatically set by Claude Code when invoking a plugin command

CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT}" python tools/build_migrate.py $ARGUMENTS
```

If `tools/build_migrate.py` does not exist in the target repo yet (plugin was
installed but `build_migrate.py` was added in a later version), fall back to
running from the plugin scaffold directly:

```bash
if [ ! -f tools/build_migrate.py ]; then
  echo "INFO: tools/build_migrate.py not found in target repo — running from plugin scaffold."
  CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT}" python "${CLAUDE_PLUGIN_ROOT}/scaffold/tools/build_migrate.py" $ARGUMENTS
fi
```

## Synthèse à l'utilisateur

Display a concise summary (≤ 10 lines) after the script completes:

- How many keys are missing from `dt-config.yaml` (section A)
- How many anchors are missing from `docs/dt-clinical-context.md` (section B)
- How many items have incomplete frontmatter (section C, read-only)
- How many `tools/build_*.py` scripts are missing or outdated (section D)
- Location of the full report: `docs/generated/migration-report.md`
  (or note if `--stdout` was used)
- If changes were applied (`--apply`): confirm what was written
- Next recommended action:
  - If gaps remain after dry-run: suggest `/doc-migrate --apply`
  - If scripts are missing/outdated: suggest `/doc-init --update`
  - If items have schema gaps: suggest reviewing section C of the report
    and editing manually or with `@risk-analyst refresh <ID>`

## Garde-fous

- **Never** overwrite existing content in `dt-config.yaml` or
  `docs/dt-clinical-context.md`.
- **Never** touch any item under `docs/items/`.
- `--apply` is additive only: it appends, never replaces.
- If the script exits with a non-zero code, surface the error verbatim.
