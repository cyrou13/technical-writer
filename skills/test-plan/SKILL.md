---
name: test-plan
description: Convention pour produire un Software Test Description (STD) IEEE 829 / IEC 62304 §5.5/§5.7 à partir des items TC. À invoquer pour générer ou comprendre le livrable docs/generated/30_STD.md.
---

# STD — Software Test Description

`docs/generated/30_STD.md` est un **Software Test Description** au sens
IEEE 829-2008 / IEC 62304 §5.5 (vérif unitaire) / §5.7 (test système).
Il est régénéré à chaque `python tools/build_docs.py` ; **ne pas
l'éditer à la main**.

## Sources d'entrée

- **Items TC** (`docs/items/TC/*.md`) — groupés par `type` (Unit /
  Integration / System).
- **Codemap** (`docs/generated/_codemap.md`) — pour les frameworks
  détectés.
- **`docs/test_plan_intro.md`** (optionnel) — sections narratives
  inline-ées par le build.

## Structure produite

1. **Introduction** — objet, références, niveaux couverts.
2. **Environnement de test** — frameworks détectés (depuis
   `package.json` / `pyproject.toml`).
3. **Stratégie de test** — issue de `test_plan_intro.md` section
   `## test-strategy`, sinon placeholder `[TODO]`.
4. **Critères de pass/fail** — par défaut un set conservateur ;
   surchargeable par `## test-pass-fail` dans l'intro.
5. **Couverture** — table par niveau (#TC, #SRS Must couverts).
6. **Cas de test** — table par niveau (ID, titre, `verifies`,
   automated).
7. **Exclusions** — issues de `## test-exclusions`, sinon `[TODO]`.

Annexe A : détail complet de chaque TC (titre, statut, version,
vérifie/mitige, source, corps Markdown).

## Format de `docs/test_plan_intro.md`

Markdown avec sections H2 dont l'ID (le slug après `## `) est utilisé
par le build comme clé. Sections reconnues :

```markdown
## test-strategy
[Inline-é dans Section 3 du STD.]

## test-pass-fail
[Inline-é dans Section 4 — surcharge le défaut.]

## test-exclusions
[Inline-é dans Section 7.]
```

Tout autre H2 est ignoré silencieusement.

## Niveaux de test

`type` valeurs admises : `Unit`, `Integration`, `System`. TC sans
`type` = `Unit` par défaut.

Class A — IEC 62304 §5.6 (intégration) est allégé. Si tu n'as pas
encore de TC `Integration`, ce n'est pas bloquant ; le STD le reflète
proprement (table de couverture vide pour ce niveau).

## Critères de pass/fail par défaut

- **PASS** — tous les TC `Must` exécutés et passants ; aucun TC
  orphelin (sans `verifies`).
- **FAIL** — ≥ 1 TC vérifiant un SRS Must en échec.
- **Skipped** — tracé, ne compte pas comme pass.

Le STD v1 ne consomme **pas** les résultats d'exécution. Si l'utilisateur
souhaite un Software Test Report (STR) séparé qui parse un junit.xml,
c'est une extension v2.

## Garde-fous

- Ne jamais éditer `30_STD.md` à la main — le build écrase.
- L'intro `test_plan_intro.md` est versionnée mais **maintenue à la
  main** : aucun agent ne la modifie.
- Si l'intro contient un `[TODO]`, il apparaît tel quel dans le STD —
  c'est intentionnel (visibilité).
