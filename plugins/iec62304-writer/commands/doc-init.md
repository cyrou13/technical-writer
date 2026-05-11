---
description: Scaffolde le repo courant pour utiliser le pipeline 62304 — copie tools/build_docs.py, docs/templates/, docs/test_plan_intro.md et crée la structure docs/items/. À lancer une seule fois par repo cible.
---

## OUTPUT LANGUAGE — STRICT

All artifacts written by this command (every file under `docs/`, item
frontmatter values such as `title`/`description`, body content,
`[TODO]`/`[GAP-...]` markers, and aggregated reports) MUST be written
in **English**, regardless of the user's conversational language or
any global `CLAUDE.md` instruction. Conversational replies to the user
MAY follow the user's language; written outputs are English-only. This
applies to every sub-agent and skill invoked from this command.

L'utilisateur veut initialiser un repo avec le pipeline de doc IEC 62304.

Arguments possibles dans `$ARGUMENTS` :
- `--update` : remplacer `tools/build_docs.py` même s'il existe.
- `--with-examples` : copier les items d'exemple
  (SRS-EXAMPLE-001, SDS, TC, RSK, THR) dans `docs/items/`.

## Étapes

### 1. Vérifications préalables

**Git n'est PAS un prérequis.** Le scaffolding fonctionne dans n'importe
quel dossier (workspace, monorepo, dossier nu). La détection ci-dessous
est purement informationnelle.

Lancer un bash bloc :

```bash
# Seule erreur bloquante : on est DANS le plugin lui-même
if [ -d .claude-plugin ]; then
  echo "ERREUR : ce répertoire est le plugin lui-même. Lance /doc-init dans le repo CIBLE." >&2
  exit 1
fi

# Détection git — informationnelle uniquement. Scan jusqu'à 3 niveaux
# (gère les layouts type cina-compose/apps/front/.git, monorepos, etc.).
GIT_REPOS=()
if git rev-parse --git-dir >/dev/null 2>&1; then
  GIT_REPOS+=("$(pwd) (top-level)")
fi
while IFS= read -r d; do
  GIT_REPOS+=("${d%/.git}/")
done < <(find . -maxdepth 3 -type d -name .git 2>/dev/null | grep -v "^\./\.git$" || true)

if [ ${#GIT_REPOS[@]} -eq 0 ]; then
  echo "Info : aucun repo git détecté. Le scaffolding continue."
  echo "  (Git est conseillé pour versionner docs/, mais pas exigé.)"
else
  echo "Repos git détectés :"
  printf '  - %s\n' "${GIT_REPOS[@]}"
  if [ ${#GIT_REPOS[@]} -gt 1 ]; then
    echo
    echo "Mode multi-repo : les agents préfixeront les chemins source: par"
    echo "le nom du composant (ex. 'front/src/auth/oauth.ts')."
  fi
fi

echo "OK — repo cible : $(pwd)"
```

**INSTRUCTION STRICTE pour Claude** : quel que soit le résultat de la
détection git ci-dessus (aucun repo, un seul, plusieurs, info, warning),
**passer à l'étape 2 sans demander confirmation**. La seule condition
d'arrêt est l'erreur explicite `[ -d .claude-plugin ]`.

### 2. Copier les assets de scaffolding

Lancer un bash bloc qui copie depuis `${CLAUDE_PLUGIN_ROOT}/scaffold/`
vers le CWD avec des règles d'idempotence :

```bash
ARGS="$ARGUMENTS"
UPDATE=0
WITH_EXAMPLES=0
case " $ARGS " in *" --update "*) UPDATE=1 ;; esac
case " $ARGS " in *" --with-examples "*) WITH_EXAMPLES=1 ;; esac

mkdir -p tools docs/templates docs/items/MAP docs/items/SRS docs/items/SDS docs/items/TC docs/items/RSK docs/items/PRSK docs/items/THR docs/items/USC docs/items/URSK

CREATED=()
SKIPPED=()

# _lib.py — shared helpers, always overwrite (no user-edited content)
cp "${CLAUDE_PLUGIN_ROOT}/scaffold/tools/_lib.py" tools/_lib.py
if [ ! -f tools/_lib.py ]; then
  CREATED+=("tools/_lib.py")
else
  CREATED+=("tools/_lib.py (refreshed)")
fi

# build_docs.py — overwrite uniquement si --update
if [ ! -f tools/build_docs.py ] || [ "$UPDATE" = "1" ]; then
  cp "${CLAUDE_PLUGIN_ROOT}/scaffold/tools/build_docs.py" tools/build_docs.py
  CREATED+=("tools/build_docs.py")
else
  SKIPPED+=("tools/build_docs.py (existe — utilise --update pour remplacer)")
fi

# build_export.py — overwrite uniquement si --update
if [ ! -f tools/build_export.py ] || [ "$UPDATE" = "1" ]; then
  cp "${CLAUDE_PLUGIN_ROOT}/scaffold/tools/build_export.py" tools/build_export.py
  CREATED+=("tools/build_export.py")
else
  SKIPPED+=("tools/build_export.py (existe — utilise --update pour remplacer)")
fi

# build_risk_export.py — overwrite uniquement si --update
if [ ! -f tools/build_risk_export.py ] || [ "$UPDATE" = "1" ]; then
  cp "${CLAUDE_PLUGIN_ROOT}/scaffold/tools/build_risk_export.py" tools/build_risk_export.py
  CREATED+=("tools/build_risk_export.py")
else
  SKIPPED+=("tools/build_risk_export.py (existe — utilise --update pour remplacer)")
fi

# build_risk_xlsx.py — overwrite uniquement si --update
if [ ! -f tools/build_risk_xlsx.py ] || [ "$UPDATE" = "1" ]; then
  cp "${CLAUDE_PLUGIN_ROOT}/scaffold/tools/build_risk_xlsx.py" tools/build_risk_xlsx.py
  CREATED+=("tools/build_risk_xlsx.py")
else
  SKIPPED+=("tools/build_risk_xlsx.py (existe — utilise --update pour remplacer)")
fi

# build_stp_export.py — overwrite uniquement si --update
if [ ! -f tools/build_stp_export.py ] || [ "$UPDATE" = "1" ]; then
  cp "${CLAUDE_PLUGIN_ROOT}/scaffold/tools/build_stp_export.py" tools/build_stp_export.py
  CREATED+=("tools/build_stp_export.py")
else
  SKIPPED+=("tools/build_stp_export.py (existe — utilise --update pour remplacer)")
fi

# build_sdd_export.py — overwrite uniquement si --update
if [ ! -f tools/build_sdd_export.py ] || [ "$UPDATE" = "1" ]; then
  cp "${CLAUDE_PLUGIN_ROOT}/scaffold/tools/build_sdd_export.py" tools/build_sdd_export.py
  CREATED+=("tools/build_sdd_export.py")
else
  SKIPPED+=("tools/build_sdd_export.py (existe — utilise --update pour remplacer)")
fi

# build_stdr_export.py — overwrite uniquement si --update
if [ ! -f tools/build_stdr_export.py ] || [ "$UPDATE" = "1" ]; then
  cp "${CLAUDE_PLUGIN_ROOT}/scaffold/tools/build_stdr_export.py" tools/build_stdr_export.py
  CREATED+=("tools/build_stdr_export.py")
else
  SKIPPED+=("tools/build_stdr_export.py (existe — utilise --update pour remplacer)")
fi

# build_str_export.py — overwrite uniquement si --update
if [ ! -f tools/build_str_export.py ] || [ "$UPDATE" = "1" ]; then
  cp "${CLAUDE_PLUGIN_ROOT}/scaffold/tools/build_str_export.py" tools/build_str_export.py
  CREATED+=("tools/build_str_export.py")
else
  SKIPPED+=("tools/build_str_export.py (existe — utilise --update pour remplacer)")
fi

# test-results.example.json — copié uniquement si absent (exemple CI — jamais overwrite)
if [ ! -f test-results.example.json ]; then
  cp "${CLAUDE_PLUGIN_ROOT}/scaffold/test-results.example.json" test-results.example.json
  CREATED+=("test-results.example.json")
else
  SKIPPED+=("test-results.example.json (existe)")
fi

# Templates — ne jamais overwrite
for tpl in map-item srs-item sds-item tc-item rsk-item prsk-item thr-item usc-item ursk-item; do
  src="${CLAUDE_PLUGIN_ROOT}/scaffold/docs/templates/${tpl}.template.md"
  dst="docs/templates/${tpl}.template.md"
  if [ ! -f "$dst" ]; then
    cp "$src" "$dst"
    CREATED+=("$dst")
  else
    SKIPPED+=("$dst (existe)")
  fi
done

# test_plan_intro.md — JAMAIS overwrite (maintenu à la main)
if [ ! -f docs/test_plan_intro.md ]; then
  cp "${CLAUDE_PLUGIN_ROOT}/scaffold/docs/test_plan_intro.md" docs/test_plan_intro.md
  CREATED+=("docs/test_plan_intro.md")
else
  SKIPPED+=("docs/test_plan_intro.md (existe — fichier maintenu à la main)")
fi

# dt-config.yaml — JAMAIS overwrite (config QMS-side)
if [ ! -f dt-config.yaml ]; then
  cp "${CLAUDE_PLUGIN_ROOT}/scaffold/dt-config.yaml" dt-config.yaml
  CREATED+=("dt-config.yaml")
else
  SKIPPED+=("dt-config.yaml (existe — config QMS maintenue à la main)")
fi

# dt-clinical-context.md — JAMAIS overwrite (sections narratives QMS)
if [ ! -f docs/dt-clinical-context.md ]; then
  cp "${CLAUDE_PLUGIN_ROOT}/scaffold/docs/dt-clinical-context.md" docs/dt-clinical-context.md
  CREATED+=("docs/dt-clinical-context.md")
else
  SKIPPED+=("docs/dt-clinical-context.md (existe — fichier maintenu à la main)")
fi

# .gitkeep par catégorie
for cat in MAP SRS SDS TC RSK PRSK THR USC URSK; do
  if [ ! -f "docs/items/$cat/.gitkeep" ]; then
    : > "docs/items/$cat/.gitkeep"
    CREATED+=("docs/items/$cat/.gitkeep")
  fi
done

# Examples
if [ "$WITH_EXAMPLES" = "1" ]; then
  for cat in MAP SRS SDS TC RSK PRSK THR USC URSK; do
    for src in "${CLAUDE_PLUGIN_ROOT}/examples/$cat"/*.md; do
      [ -f "$src" ] || continue
      name=$(basename "$src")
      dst="docs/items/$cat/$name"
      if [ ! -f "$dst" ]; then
        cp "$src" "$dst"
        CREATED+=("$dst")
      else
        SKIPPED+=("$dst (existe)")
      fi
    done
  done
fi

# .gitignore — append sans dupliquer
touch .gitignore
for line in "__pycache__/" "*.pyc" ".venv/" "venv/"; do
  if ! grep -qxF "$line" .gitignore; then
    echo "$line" >> .gitignore
    CREATED+=(".gitignore (+ $line)")
  fi
done

echo
echo "=== Créés ==="
printf '  %s\n' "${CREATED[@]}"
echo
echo "=== Sautés ==="
printf '  %s\n' "${SKIPPED[@]}"
```

### 3. Synthèse à l'utilisateur

Afficher en ≤ 10 lignes :
- nombre de fichiers créés vs sautés,
- emplacements clés (`tools/build_docs.py`, `tools/build_export.py`,
  `dt-config.yaml`, `docs/items/`, `docs/templates/`),
- prochain pas : `/doc-62304` pour lancer le pipeline complet, ou
  `/doc-item SRS-XXX-001 "..."` pour créer un item à la main,
- rappel : éditer `dt-config.yaml` (signatures, références, format d'ID)
  AVANT de lancer `/doc-62304` si on veut un format d'ID Avicenna-style,
- rappel : éditer `docs/dt-clinical-context.md` pour remplir les
  sections narratives QMS (intended use, warnings, etc.) avant
  `/doc-export`,
- rappel : éditer `docs/test_plan_intro.md` pour remplir les sections
  narratives du STD.

## Garde-fous

- **Jamais** overwrite `docs/test_plan_intro.md` ni les items utilisateur.
- **Jamais** overwrite les templates s'ils existent (l'utilisateur peut
  les avoir customisés).
- `--update` ne touche QUE `tools/build_docs.py`.
- Si le bloc bash échoue, ne pas masquer la sortie d'erreur.
