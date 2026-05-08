---
description: Scaffolde le repo courant pour utiliser le pipeline 62304 — copie tools/build_docs.py, docs/templates/, docs/test_plan_intro.md et crée la structure docs/items/. À lancer une seule fois par repo cible.
---

L'utilisateur veut initialiser un repo avec le pipeline de doc IEC 62304.

Arguments possibles dans `$ARGUMENTS` :
- `--update` : remplacer `tools/build_docs.py` même s'il existe.
- `--with-examples` : copier les items d'exemple
  (SRS-EXAMPLE-001, SDS, TC, RSK, THR) dans `docs/items/`.

## Étapes

### 1. Vérifications préalables

Lancer un bash bloc :

```bash
# Ne pas s'auto-scaffolder dans le plugin
if [ -d .claude-plugin ]; then
  echo "ERREUR : ce répertoire est le plugin lui-même. Lance /doc-init dans le repo CIBLE." >&2
  exit 1
fi

# Détection multi-repo : git au CWD + sous-dossiers contenant .git/
GIT_REPOS=()
if git rev-parse --git-dir >/dev/null 2>&1; then
  GIT_REPOS+=("$(pwd) (top-level)")
fi
for d in */; do
  d="${d%/}"
  [ -d "$d/.git" ] && GIT_REPOS+=("$d/")
done

if [ ${#GIT_REPOS[@]} -eq 0 ]; then
  echo "AVERTISSEMENT : aucun repo git détecté ici ni dans les sous-dossiers." >&2
  echo "  Le scaffolding va continuer ; tu voudras 'git init' à un moment pour" >&2
  echo "  versionner docs/ (la traçabilité 62304 dépend de l'historique git)." >&2
elif [ ${#GIT_REPOS[@]} -gt 1 ]; then
  echo "Mode multi-repo détecté :"
  printf '  - %s\n' "${GIT_REPOS[@]}"
  echo
  echo "Les items vivront à la racine du projet (ici : $(pwd))."
  echo "Les agents écriront des chemins source: préfixés par le nom du sous-repo,"
  echo "ex. 'front/src/auth/oauth.ts' ou 'back/src/api.py'."
fi

echo "OK — repo cible : $(pwd)"
```

### 2. Copier les assets de scaffolding

Lancer un bash bloc qui copie depuis `${CLAUDE_PLUGIN_ROOT}/scaffold/`
vers le CWD avec des règles d'idempotence :

```bash
ARGS="$ARGUMENTS"
UPDATE=0
WITH_EXAMPLES=0
case " $ARGS " in *" --update "*) UPDATE=1 ;; esac
case " $ARGS " in *" --with-examples "*) WITH_EXAMPLES=1 ;; esac

mkdir -p tools docs/templates docs/items/SRS docs/items/SDS docs/items/TC docs/items/RSK docs/items/THR

CREATED=()
SKIPPED=()

# build_docs.py — overwrite uniquement si --update
if [ ! -f tools/build_docs.py ] || [ "$UPDATE" = "1" ]; then
  cp "${CLAUDE_PLUGIN_ROOT}/scaffold/tools/build_docs.py" tools/build_docs.py
  CREATED+=("tools/build_docs.py")
else
  SKIPPED+=("tools/build_docs.py (existe — utilise --update pour remplacer)")
fi

# Templates — ne jamais overwrite
for tpl in srs-item sds-item tc-item rsk-item thr-item; do
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

# .gitkeep par catégorie
for cat in SRS SDS TC RSK THR; do
  if [ ! -f "docs/items/$cat/.gitkeep" ]; then
    : > "docs/items/$cat/.gitkeep"
    CREATED+=("docs/items/$cat/.gitkeep")
  fi
done

# Examples
if [ "$WITH_EXAMPLES" = "1" ]; then
  for cat in SRS SDS TC RSK THR; do
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

Afficher en ≤ 8 lignes :
- nombre de fichiers créés vs sautés,
- emplacements clés (`tools/build_docs.py`, `docs/items/`, `docs/templates/`),
- prochain pas : `/doc-62304` pour lancer le pipeline complet, ou
  `/doc-item SRS-XXX-001 "..."` pour créer un item à la main,
- rappel : éditer `docs/test_plan_intro.md` pour remplir les sections
  narratives du STD.

## Garde-fous

- **Jamais** overwrite `docs/test_plan_intro.md` ni les items utilisateur.
- **Jamais** overwrite les templates s'ils existent (l'utilisateur peut
  les avoir customisés).
- `--update` ne touche QUE `tools/build_docs.py`.
- Si le bloc bash échoue, ne pas masquer la sortie d'erreur.
