---
description: Agrège les items en docs imprimables (SRS/SDS/Tests/Traçabilité) et calcule la couverture. Idempotent.
---

Exécute `python tools/build_docs.py` à la racine du repo.

## Étapes

1. Vérifier que Python 3 est dispo (`python --version` ou `python3 --version`).

2. Lancer le build : `python tools/build_docs.py` (utiliser `python3` si
   nécessaire).

3. Si le script retourne ≠ 0 → afficher la sortie d'erreur, ne pas
   masquer.

4. Si OK → résumer en ≤ 8 lignes :
   - nombre d'items lus par catégorie,
   - métriques de couverture (depuis `coverage.json`),
   - chemins des fichiers produits dans `docs/generated/`.

## Argument optionnel

`$ARGUMENTS` peut contenir `--strict`, qui demande au script d'échouer
sur tout `[TODO]` ou `[GAP-62304]` non traité (utile en CI).
