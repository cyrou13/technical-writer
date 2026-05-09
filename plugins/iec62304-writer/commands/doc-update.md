---
description: Met à jour la doc 62304 après évolution du code — détecte orphelins, items stale, gaps de couverture, puis re-traite uniquement le différentiel. Optionnel — passer un label `Vx.y` pour bump majeur global (ex. /doc-update V2.0).
---

L'utilisateur veut **mettre à jour** la doc existante après évolution du
code, PAS regénérer from scratch. Idempotent : si rien n'a changé, rien
n'est modifié.

Argument optionnel dans `$ARGUMENTS` :
- `Vx.y` (ex. `V2.0`, `V1.5`) : bump majeur global. Tous les items
  modifiés à l'étape 3 ou 4 voient leur `version` alignée sur ce label
  (`x.y.0`), et tout `Approved` modifié repasse à `Draft` pour
  re-approbation.

## Étapes

### 1. Cartographier (refresh)

Lancer le sub-agent `code-archeologist`. Il met à jour
`docs/generated/_codemap.md` avec l'état actuel du repo.

### 2. Diff (cadrage)

Lancer le sub-agent `doc-updater`. Il :
- déprécie les orphelins (édition idempotente),
- nettoie les orphelins partiels (édition idempotente),
- liste les items stale et les gaps dans
  `docs/generated/_update_diff.md`.

**Bloquant.** Lire le rapport. Si tout est vide → afficher "Doc déjà à
jour" et sauter directement à l'étape 6 (build).

### 3. Re-traitement ciblé des writers

Lancer **uniquement** les writers concernés par le diff (paralleliser
ceux qui n'ont pas de dépendance entre eux) :

- Si gaps SRS ou stale SRS → `requirements-writer`.
- Si gaps SDS ou stale SDS → `architecture-writer`.
- Si gaps TC ou stale TC → `test-evidence-collector`.
- Si **rien** dans une catégorie → ne pas lancer ce writer (gain de
  temps).

Les writers sont idempotents : ils re-lisent les items existants, ne
modifient que ceux qui en ont besoin, créent les manquants.

Ordre :
- `requirements-writer` d'abord (les autres lisent les SRS).
- Puis `architecture-writer` + `test-evidence-collector` en parallèle.

### 4. Re-évaluation des risques

Si **n'importe quel** item SRS / SDS / TC a été modifié à l'étape 3,
lancer **`risk-analyst`** PUIS **`security-analyst`** (séquence, pas
parallèle — le security-analyst utilise les RSK pour le linkage
`triggers`).

Ces agents :
- relisent les items modifiés,
- vérifient si les contrôles existants (`links.mitigates`) tiennent
  toujours après les changements,
- mettent à jour `residual_acceptable` si nécessaire,
- ajoutent un GAP marker si un risque devient non-acceptable.

Si **rien** n'a bougé en SRS/SDS/TC → sauter cette étape.

### 5. Bump majeur (si argument `Vx.y`)

Pour chaque item modifié aux étapes 3 ou 4, aligner la version sur le
label demandé :

- `version: x.y.0` (le label vient de l'argument).
- Si l'item était `status: Approved` → repasser à `Draft`.
- Ajouter une ligne au `## Changelog` du corps :
  ```markdown
  - YYYY-MM-DD vx.y.0 : alignement majeur Vx.y — <résumé court du diff>
  ```

Si pas d'argument `Vx.y`, les writers gèrent les bumps version à leur
granularité naturelle (patch/minor selon les règles `items-store`).

### 6. Build

`python tools/build_docs.py`. Vérifier que tous les agrégats sont
régénérés.

### 7. Revue

Lancer `compliance-reviewer`. Il écrit
`docs/generated/99_compliance_review.md`.

### 8. Synthèse à l'utilisateur (≤ 16 lignes)

- Items dépréciés (orphelins totaux) : N — listés.
- Orphelins partiels nettoyés : N.
- Items stale re-traités : N.
- Gaps de couverture créés : N.
- RSK / THR dont `residual_acceptable` a changé : N — alerter si > 0.
- Métriques avant/après si possible (lire l'ancien `coverage.json` du
  build précédent depuis git, comparer au nouveau).
- Chemins des principaux livrables.
- Si bump `Vx.y` appliqué : nombre d'items alignés.

## Garde-fous

- **Idempotence stricte** : si le code n'a pas évolué, /doc-update
  produit 0 modification d'item. Le rapport `_update_diff.md` contient
  alors "Doc déjà à jour".
- **Pas de suppression d'items.** Jamais. Toujours `Deprecated`.
- Si `_codemap.md` n'est pas produit à l'étape 1 → arrêter.
- Si le build échoue à l'étape 6 → afficher l'erreur Python, ne pas
  masquer.
- L'argument `Vx.y` ne touche QUE les items modifiés à cette passe — il
  ne renumérote pas les items inchangés (qui gardent leur version).
- Ne jamais commit/push (sauf demande explicite). Toute la sortie est
  locale.
