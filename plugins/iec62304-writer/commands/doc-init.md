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
