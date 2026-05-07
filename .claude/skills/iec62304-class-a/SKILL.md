---
name: iec62304-class-a
description: Référentiel des livrables IEC 62304 Classe A et de leur contenu minimal. À invoquer dès qu'un agent génère, met à jour ou revoit de la documentation technique conforme 62304 Classe A.
---

# IEC 62304 — Classe A — référentiel

Ce skill est la **source de vérité** pour le contenu des livrables. Le
**stockage** est défini par le skill `items-store` (item-per-file, IDs
stables, liens de traçabilité — équivalents locaux de Matrix Requirements).

## Classe A — rappel

Aucune blessure ni atteinte à la santé n'est possible. Périmètre 62304
allégé, mais structure documentaire conservée.

## Livrables v1 (périmètre du workflow)

| Clause | Livrable | Catégorie d'items | Fichier agrégé |
|---|---|---|---|
| §5.1 | Plan de développement | — | `docs/generated/00_dev_plan.md` |
| §5.2 | Software Requirements (SRS) | `SRS` | `docs/generated/10_SRS.md` |
| §5.3–§5.4 | Software Design / Architecture (SDS) | `SDS` | `docs/generated/20_SDS.md` |
| §5.5 / §5.7 | Vérification (test plan + preuves) | `TC` | `docs/generated/30_test_evidence.md` |
| §5.1.1 / §5.2.6 | Matrice de traçabilité | (calculée) | `docs/generated/40_traceability.md` |

## Règles de rédaction

1. **Pas d'invention.** Toute affirmation est traçable à un fichier source,
   un test, ou un commentaire taggé. Sinon : marqueur `[TODO]`, jamais
   fabriquer une exigence.
2. **Phrases testables.** `shall` / `doit` + critère mesurable. Pas de
   "rapide", "facile", "intuitif".
3. **Pas de duplication** SRS ↔ SDS — *quoi* vs *comment*.
4. **IDs immuables.** Voir `items-store`. Une exigence retirée passe à
   `Deprecated`, jamais supprimée.
5. **Atomicité.** Un item = une exigence / un module / un cas de test.

## Champs minimaux

Voir `items-store` pour le schéma complet. Rappel des minima :

- **SRS** : `id`, `title`, `description`, `verification`, `source`, `status`
- **SDS** : `id`, `module`, `responsibility`, `interfaces`, `implements`,
  `source`
- **TC** : `id`, `title`, `verifies`, `steps`, `expected`, `source`

## Marqueurs de gap

Quand un livrable ne peut pas être complété :

```
> [GAP-62304] §5.2.2 — <explication> — <action requise par l'utilisateur>
```

Le `compliance-reviewer` agrège ces marqueurs.

## Ce qui n'est PAS couvert v1

- Gestion des risques détaillée (§7) — Classe A : identification suffisante.
- Gestion de configuration (§8) — assurée par git.
- Résolution des problèmes (§9) — assurée par l'issue tracker.

Si le périmètre évolue (Classe B/C, gestion des SOUP), créer un skill
`iec62304-class-b` ou étendre celui-ci.
