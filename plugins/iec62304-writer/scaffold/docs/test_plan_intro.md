<!--
  Sections narratives du Software Test Description (STD).
  Le build (`tools/build_docs.py`) inline les sections ci-dessous dans
  `docs/generated/30_STD.md`.

  Sections reconnues :
    ## test-strategy   → Section 3 du STD
    ## test-pass-fail  → Section 4 (surcharge le défaut)
    ## test-exclusions → Section 7

  Tout autre H2 est ignoré. Édite à la main — aucun agent n'y touche.
-->

## test-strategy

[TODO Décrire la stratégie de test :

- niveaux ciblés (unit / intégration / système / E2E),
- méthode (TDD/BDD/test-after, exigence de couverture),
- outillage (Vitest/Jest, pytest, Playwright/Cypress…),
- fréquence et déclencheurs (pre-commit, CI sur PR, nightly),
- périmètre de l'automatisation vs tests manuels,
- gestion des fixtures et données de test.]

## test-exclusions

[TODO Lister ce qui n'est PAS testé en automatique et pourquoi :

- composants tiers traités en boîte noire (avec justification),
- environnements non couverts (mobile, navigateurs anciens…),
- scénarios de charge / performance hors périmètre v1,
- tests d'accessibilité reportés.]
