---
description: Génère le livrable Software Test Plan (STP) habillé pour le dossier technique (cover, signatures, références, sections narratives, table des TC planifiés) à partir des items TC et de `dt-config.yaml`. Sortie dans `docs/export/`.
---

## OUTPUT LANGUAGE — STRICT

All artifacts written by this command (the exported STP Markdown, the
optional `.docx`, the export log) MUST be written in **English**,
regardless of the user's conversational language or any global
`CLAUDE.md` instruction. Conversational replies MAY follow the user's
language; written outputs are English-only.

Exécute `python tools/build_stp_export.py` à la racine du repo cible et
rapporte les résultats. Le script lit `dt-config.yaml`,
`docs/dt-clinical-context.md`, les items sous `docs/items/TC/` et
optionnellement `docs/generated/coverage.json`, puis écrit le livrable
dans `docs/export/`.

## Étapes

### 1. Vérifications préalables

```bash
# dt-config.yaml requis (le script peut tourner sans, mais on prévient l'utilisateur)
if [ ! -f dt-config.yaml ]; then
  echo "Avertissement : dt-config.yaml manquant. Lance /doc-init pour le scaffolder."
  echo "L'export va utiliser des valeurs par défaut et insérer [TODO] partout."
fi

# dt-clinical-context.md fortement recommandé
if [ ! -f docs/dt-clinical-context.md ]; then
  echo "Avertissement : docs/dt-clinical-context.md manquant. Les sections narratives"
  echo "(test environment, schedule, qualification) seront des TODO yellow dans l'export."
fi

# coverage.json recommandé (produit par /doc-build)
if [ ! -f docs/generated/coverage.json ]; then
  echo "Avertissement : docs/generated/coverage.json manquant."
  echo "Lance /doc-build d'abord pour remplir §3.3 et §4.1.1 avec les métriques de couverture."
fi

# Items TC — bloquant si aucun
if ! ls docs/items/TC/*.md >/dev/null 2>&1; then
  echo "ERREUR : aucun item TC sous docs/items/TC/. Lance /doc-62304 d'abord." >&2
  exit 1
fi
```

### 2. Lancer le build

```bash
python tools/build_stp_export.py
```

Si `python3` est nécessaire à la place de `python`, ré-essayer
automatiquement. Si le script échoue : afficher la sortie d'erreur,
ne pas masquer.

### 3. Rendu .docx (si applicable)

Le script `build_stp_export.py` invoque pandoc lui-même si
`dt-config.yaml: rendering.reference_docx` est défini et pandoc est
disponible. Pas d'action côté Claude.

### 4. Synthèse à l'utilisateur (≤ 12 lignes)

- Chemin du livrable Markdown produit (`docs/export/<identifier>-STP.md`),
- Chemin du `.docx` si produit, ou raison de non-production (pandoc
  absent, `reference_docx` non défini),
- Nombre de TC inclus / exclus (deprecated),
- Nombre de SRS chargés (pour la table de couverture §4.1.1),
- Sections `<mark>[TODO ...]</mark>` détectées dans le rendu (alerter si > 0 — à remplir dans `dt-clinical-context.md`),
- Chemin du log : `docs/export/<identifier>-stp-export.log`.

## Argument optionnel

`$ARGUMENTS` peut contenir :
- `--strict` : exit ≠ 0 si l'export contient des `<mark>[TODO ...]</mark>`.
  Utile en CI avant soumission RAQA.
- `--md-only` : ne pas tenter le rendu .docx même si pandoc est dispo.

## Garde-fous

- Ne JAMAIS modifier les items sous `docs/items/` ni les sorties de
  `/doc-build` sous `docs/generated/`.
- L'export est **complémentaire** à `/doc-build`, pas un remplacement :
  `/doc-build` produit `30_STD.md` (agrégat interne), `/doc-stp-export`
  produit le livrable QMS STP.
- Ne JAMAIS commit ou push automatiquement — la sortie reste locale.
- Si `dt-config.yaml: approvals` contient encore des `[TODO]` ET le
  livrable est généré → logger un warning bloquant en mode `--strict`.
