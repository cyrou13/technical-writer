---
description: Génère le triplet de livrables IEC 62366-1 — Usability Engineering File (UEF), Summative Evaluation (USE), et UEF Annex 1 (IECEE checklist) — à partir des items USC, URSK, SRS-USE-* et de `dt-config.yaml`. Sortie dans `docs/export/`. Supporte `platform-rich` (SaaS multi-persona) et `clinical-narrow` (AI clinique étroit type CSpine).
---

## OUTPUT LANGUAGE — STRICT

All artifacts written by this command (the exported UEF / USE /
UEF-Annex1 Markdowns, the optional `.docx` files, the export log)
MUST be written in **English**, regardless of the user's
conversational language or any global `CLAUDE.md` instruction.
Conversational replies MAY follow the user's language; written
outputs are English-only.

Exécute `python tools/build_use_export.py` à la racine du repo cible
et rapporte les résultats. Le script lit `dt-config.yaml`,
`docs/dt-clinical-context.md`, les items sous `docs/items/USC/`,
`docs/items/URSK/`, `docs/items/SRS/`, et les boilerplates sous
`docs/static/`, puis écrit le triplet dans `docs/export/`.

## Vérifications préalables

```bash
if [ -d .claude-plugin ]; then
  echo "ERROR: this directory is the plugin itself. Run from the TARGET repo." >&2
  exit 1
fi

# dt-config.yaml requis
if [ ! -f dt-config.yaml ]; then
  echo "Avertissement : dt-config.yaml manquant. Lance /doc-init pour le scaffolder."
  echo "L'export va utiliser des valeurs par défaut et insérer [TODO] partout."
fi

# dt-clinical-context.md fortement recommandé
if [ ! -f docs/dt-clinical-context.md ]; then
  echo "Avertissement : docs/dt-clinical-context.md manquant. Les sections cliniques"
  echo "(intended use, medical purpose, patient population, etc.) seront vides."
fi

# Items USC — bloquant si aucun
if ! ls docs/items/USC/*.md >/dev/null 2>&1; then
  echo "ERREUR : aucun item USC sous docs/items/USC/. Lance /doc-62304 d'abord." >&2
  exit 1
fi

# Items URSK — warning si aucun (le triplet reste générable mais §3.2/3.4 seront vides)
if ! ls docs/items/URSK/*.md >/dev/null 2>&1; then
  echo "Avertissement : aucun item URSK sous docs/items/URSK/."
  echo "Le UEF §3.2 (use errors) et §3.4 (mitigation) seront vides."
fi
```

## Exécution

```bash
if [ -f tools/build_use_export.py ]; then
  python tools/build_use_export.py $ARGUMENTS
else
  echo "INFO: tools/build_use_export.py not found — running from plugin scaffold."
  CLAUDE_PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT}" python "${CLAUDE_PLUGIN_ROOT}/scaffold/tools/build_use_export.py" $ARGUMENTS
fi
```

Si `python3` est nécessaire à la place de `python`, ré-essayer
automatiquement. Si le script échoue : afficher la sortie d'erreur,
ne pas masquer.

## Rendu .docx (si applicable)

Le script `build_use_export.py` invoque pandoc lui-même si
`dt-config.yaml: rendering.reference_docx` est défini et pandoc est
disponible. Pas d'action côté Claude.

## Synthèse à l'utilisateur (≤ 14 lignes)

- Mode template retenu (`platform-rich` ou `clinical-narrow`) + raison
  (override config / auto-détecté),
- 3 chemins de livrables Markdown (`docs/export/<id>-UEF.md`,
  `docs/export/<id>-USE.md`, `docs/export/<id>-UEF-Annex1.md`),
- Chemins des `.docx` si produits, ou raison de non-production (pandoc
  absent, reference_docx non défini),
- Nombre d'items USC inclus / exclus (deprecated),
- Nombre d'items URSK inclus, dont nombre flaggés pour summative,
- Nombre de URSK sans mitigation SRS (alerter si > 0 — gap),
- Sections `<mark>[TODO ...]</mark>` détectées par livrable (alerter
  si > 0),
- Chemin du log : `docs/export/<identifier>-use-export.log`,
- Rappel : compléter manuellement les `<mark>[TODO formative-history]</mark>`
  et `<mark>[TODO summative-*]</mark>` après les sessions de test.

## Arguments

- `--strict` : exit ≠ 0 si l'un des livrables contient des `<mark>[TODO]</mark>`
  ou des URSK sans mitigation SRS. Utile en CI avant submission RAQA.
- `--md-only` : ne pas tenter le rendu .docx même si pandoc est dispo.
- `--template clinical-narrow|platform-rich` : override le mode défini dans
  `dt-config.yaml: usability.template` pour ce run uniquement.
- `--only uef|use|annex1` : ne générer qu'un seul des 3 livrables (utile
  pour itérer sans tout reconstruire).

## Garde-fous

- Ne JAMAIS modifier les items sous `docs/items/` ni les sorties de
  `/doc-build` sous `docs/generated/` ni les statiques sous `docs/static/`.
- L'export est **complémentaire** à `/doc-build`, pas un remplacement —
  `/doc-build` produit l'agrégat interne `70_usability_analysis.md`,
  `/doc-use-export` produit les livrables QMS.
- Ne JAMAIS commit ou push automatiquement — la sortie reste locale.
- Si `dt-config.yaml: approvals` ou `usability.contact` contiennent
  encore des `[TODO]` ET le livrable est généré → logger un warning
  bloquant en mode `--strict`.
