---
description: Génère le livrable Risk Analysis Report (ISO 14971-compliant, équivalent annex2 Avicenna) + table d'inventaire CSV à partir des items RSK/THR/URSK et de `dt-config.yaml`. Sortie dans `docs/export/`.
---

## OUTPUT LANGUAGE — STRICT

All artifacts written by this command (the Risk Analysis Report
Markdown, the CSV inventory, the optional `.docx`, the export log)
MUST be written in **English**, regardless of the user's conversational
language or any global `CLAUDE.md` instruction. Conversational replies
MAY follow the user's language; written outputs are English-only.

Exécute `python tools/build_risk_export.py` à la racine du repo cible et
rapporte les résultats. Le script lit `dt-config.yaml`,
`docs/dt-clinical-context.md`, et les items RSK/THR/URSK sous
`docs/items/`, et écrit le livrable dans `docs/export/`.

## Étapes

### 1. Vérifications préalables

```bash
# dt-config.yaml recommandé
if [ ! -f dt-config.yaml ]; then
  echo "Avertissement : dt-config.yaml manquant. Le rapport contiendra des [TODO]."
fi

# Items RSK — bloquant si aucun
if ! ls docs/items/RSK/*.md >/dev/null 2>&1; then
  echo "ERREUR : aucun item RSK sous docs/items/RSK/. Lance /doc-62304 d'abord." >&2
  exit 1
fi

# Note informative sur les anchors clinical-context
if ! grep -q "^## end-users\|^## characteristics-affecting-safety" docs/dt-clinical-context.md 2>/dev/null; then
  echo "Info : les anchors `## end-users` et `## characteristics-affecting-safety`"
  echo "sont absents de docs/dt-clinical-context.md. Le rapport affichera [TODO]"
  echo "dans les sections §2.2 et §2.3. À ajouter avant submission RAQA."
fi
```

### 2. Lancer le build

```bash
python tools/build_risk_export.py
```

Fallback sur `python3` si nécessaire. Si le script échoue : afficher la
sortie d'erreur, ne pas masquer.

### 3. Synthèse à l'utilisateur (≤ 14 lignes)

- Chemin du Markdown produit,
- Chemin du `.docx` si produit, ou raison de non-production,
- Chemin du CSV produit,
- Nombre d'items RSK / THR / URSK inclus,
- Software safety classification déduite (Class A ou ⚠ escalation),
- Nombre de RSK avec `residual_acceptable: false` (alerte),
- Nombre de RSK avec `control_hierarchy: information_for_safety`
  (→ labeling à valider),
- Nombre de RSK avec `arising_risks` non vide (cascade),
- Nombre de sections `[TODO]` détectées dans le rendu,
- Rappel : §2.9 (Adequacy of Device Safety) et §4.3 (Benefit/Risk)
  sont des sections **non auto-générables** — jugement humain requis,
- Chemin du log.

## Argument optionnel

`$ARGUMENTS` peut contenir :
- `--strict` : exit ≠ 0 si le rendu contient des `[TODO]` ou si > 0 RSK
  ont `residual_acceptable: false`. Utile en CI avant submission RAQA.
- `--md-only` : ne pas tenter le rendu `.docx` même si pandoc est dispo.

## Garde-fous

- Ne JAMAIS modifier les items sous `docs/items/`.
- Ne JAMAIS commit/push — sortie locale.
- Si `dt-config.yaml: approvals` contient encore des `[TODO]` ET le
  livrable est généré → logger un warning bloquant en mode `--strict`.
- §2.9 (Adequacy of Device Safety and benefit-risk analysis) et §4.3
  (Benefit/Risk analysis) restent en `[TODO]` jusqu'à révision humaine —
  c'est intentionnel. Ces sections capturent le jugement final
  benefit/risk (ISO 14971 §8) qui ne peut PAS être auto-généré.
