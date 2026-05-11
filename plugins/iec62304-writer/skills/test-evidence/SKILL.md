---
name: test-evidence
description: Découvrir et formaliser les tests existants en items TC (test cases) IEC 62304 §5.5/§5.7. À invoquer pour produire docs/items/TC/ et le plan de vérification.
---

## OUTPUT LANGUAGE — STRICT

Any TC item produced while applying this skill (frontmatter values,
preconditions / steps / expected, body sections, `[TODO]`/`[GAP-...]`
markers) MUST be written in **English**, regardless of the user's
conversational language or any global `CLAUDE.md` instruction.

# Test evidence — découverte et formalisation des tests

## Découverte des tests

### TS/JS

- Vitest / Jest : `**/*.{test,spec}.{ts,tsx,js,jsx}`, fichiers sous
  `__tests__/`, config dans `vitest.config.*` / `jest.config.*`.
- Playwright / Cypress : `e2e/`, `tests/`, `cypress/`.

### Python

- Pytest : `test_*.py`, `*_test.py`, dossiers `tests/`. Config dans
  `pytest.ini`, `pyproject.toml [tool.pytest.ini_options]`,
  `setup.cfg`.
- unittest : classes héritant de `unittest.TestCase`.

## Granularité

Un fichier de test peut produire plusieurs items TC. Heuristique :

- **1 `describe`/classe de test** ≈ 1 module sous test → ne crée pas
  d'item TC seul, juste un regroupement.
- **1 `it` / `test_xxx`** = 1 cas de test → 1 item TC.

Exception : si un même `it` valide plusieurs assertions sans rapport,
scinder mentalement (ne pas modifier le code).

## Linkage `verifies`

Pour chaque TC, remplir `links.verifies:` avec les IDs SRS vérifiés.
Méthode :

1. Si le test contient un commentaire `// @verifies SRS-XXX-NNN` →
   autorité.
2. Sinon, chercher les SRS dont `source:` inclut le fichier sous test
   (souvent inférable depuis l'import principal du fichier de test).
3. Sinon, marquer `[TODO] mapping SRS à compléter` et lister dans
   `## Notes`.

## Plan de vérification (agrégat)

`docs/generated/30_STD.md` est produit par le build. Il
contient :

- liste des outils de test détectés et commandes pour les exécuter,
- table des TC groupés par module sous test,
- pour chaque TC : ID, titre, type (unit/integration/system), statut
  (`Passing` / `Failing` / `Skipped` / `Unknown`), SRS vérifié(s).

## Statut d'exécution

Le statut **réel** d'exécution n'est pas devinable sans lancer les tests.

- Par défaut : `status: Unknown` au niveau de l'item TC.
- Si l'utilisateur a fourni un rapport (`junit.xml`, sortie pytest,
  `vitest --reporter=json`), le parser et mettre à jour le statut.
- Le workflow `/doc-62304` ne lance **pas** la suite de tests
  automatiquement (côté effets de bord). Recommander à l'utilisateur de
  fournir un rapport ou de lancer `/doc-test-run` (à construire si
  besoin).

## Sortie

`docs/items/TC/TC-<DOMAIN>-<NNN>.md` avec frontmatter conforme et corps :

```markdown
## Préconditions
- ...

## Étapes
1. ...
2. ...

## Résultats attendus
- ...

## Notes
```

## Anti-patterns

- Inventer un test qui n'existe pas dans le code.
- Mettre `status: Passing` sans avoir vu un rapport d'exécution récent.
- Créer un TC sans `links.verifies:` ni marqueur `[TODO]`.
