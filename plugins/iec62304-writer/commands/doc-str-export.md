---
description: Génère le livrable STR-auto (Software Test Report automatisé) à partir du fichier test-results.json émis par CI et de dt-config.yaml. Format synthétique — plus court que le STDR. Sortie dans docs/export/.
---

## OUTPUT LANGUAGE — STRICT

All artifacts written by this command (the STR Markdown, the optional
`.docx`, the export log) MUST be written in **English**, regardless of
the user's conversational language or any global `CLAUDE.md` instruction.
Conversational replies MAY follow the user's language.

Exécute `python tools/build_str_export.py` à la racine du repo cible et
rapporte les résultats.

## Étapes

### 1. Vérifications préalables

```bash
# dt-config.yaml recommandé
if [ ! -f dt-config.yaml ]; then
  echo "Avertissement : dt-config.yaml manquant. Le rapport contiendra des [TODO]."
fi

# test-results.json — informatif
TR_PATH=$(python3 -c "
import sys, pathlib
p = pathlib.Path('dt-config.yaml')
if p.exists():
    import re
    m = re.search(r'test_results_path\s*:\s*(\S+)', p.read_text())
    print(m.group(1) if m else 'test-results.json')
else:
    print('test-results.json')
" 2>/dev/null || echo "test-results.json")

if [ ! -f "$TR_PATH" ]; then
  echo "Info : $TR_PATH absent. La section §4 contiendra un TODO yellow."
  echo "  Pour peupler les résultats, émettre test-results.json depuis CI."
  echo "  Format de référence : scaffold/test-results.example.json"
fi
```

### 2. Lancer le build

```bash
python tools/build_str_export.py $ARGUMENTS
```

Fallback sur `python3` si nécessaire. Si le script échoue, afficher la
sortie d'erreur sans la masquer.

### 3. Synthèse à l'utilisateur (≤ 12 lignes)

- Chemin du Markdown produit,
- Chemin du `.docx` si produit, ou raison de non-production,
- run_id et git_sha du run (si test-results.json trouvé),
- Résumé : total / passed / failed / skipped / not_run,
- Nombre de TC en échec avec leur ID (si failed > 0),
- Nombre de sections [TODO] dans le rendu,
- Chemin du log.

## Arguments optionnels

`$ARGUMENTS` peut contenir :
- `--strict` : exit ≠ 0 si le rendu contient des [TODO] ou si ≥ 1 TC
  est en `failed`. Utile en CI post-run pour bloquer la soumission RAQA.
- `--md-only` : ne pas tenter le rendu `.docx` même si pandoc est dispo.

## Garde-fous

- Ne JAMAIS modifier les items sous `docs/items/`.
- Ne JAMAIS commit/push — sortie locale uniquement.
- Le STR-auto est un livrable de synthèse; pour le détail TC par TC
  (description + résultats), utiliser `/doc-stdr-export`.
