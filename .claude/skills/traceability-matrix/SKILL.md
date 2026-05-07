---
name: traceability-matrix
description: Construire la matrice de traçabilité SRS ↔ SDS ↔ TC depuis les liens dans frontmatter des items, et calculer la couverture. À invoquer après que les items SRS/SDS/TC sont créés.
---

# Matrice de traçabilité — construction et lecture

## Source de vérité

Les liens sont stockés **uniquement** dans `links:` du frontmatter de
chaque item (cf. `items-store`). Ce skill ne modifie aucun lien — il
**lit** et **agrège**.

## Logique d'agrégation

Pour chaque `SRS-XYZ` :

- `implementedBy` = { SDS dont `links.implements` contient `SRS-XYZ` }
- `verifiedBy` = { TC dont `links.verifies` contient `SRS-XYZ` }

Métriques de couverture (Classe A — utiles, pas obligatoires) :

- `implementation_rate` = `#{SRS avec ≥1 implementedBy} / #SRS`
- `verification_rate` = `#{SRS avec ≥1 verifiedBy} / #SRS`
- `orphan_sds` = SDS sans `implements`
- `orphan_tc` = TC sans `verifies`
- `deprecated_links` = liens vers des items `Deprecated`

## Sortie

`docs/generated/40_traceability.md` :

```markdown
# Matrice de traçabilité

## Synthèse
| Métrique | Valeur |
|---|---|
| Exigences (SRS) | 42 |
| Couverture implémentation | 38/42 (90%) |
| Couverture vérification | 35/42 (83%) |

## SRS → SDS → TC
| SRS | Titre | SDS | TC | Statut |
|---|---|---|---|---|
| SRS-AUTH-001 | OAuth2 login | SDS-AUTH-001 | TC-AUTH-001, TC-AUTH-002 | OK |
| SRS-AUTH-002 | Logout | — | TC-AUTH-003 | ⚠ pas de SDS |

## Orphelins
### SDS sans exigence
- SDS-UTIL-007

### TC sans exigence
- TC-MISC-002
```

`docs/generated/coverage.json` (machine-readable, pour CI) :

```json
{
  "srs_count": 42,
  "implementation_rate": 0.90,
  "verification_rate": 0.83,
  "orphans": { "sds": ["SDS-UTIL-007"], "tc": ["TC-MISC-002"] }
}
```

## Implémentation effective

C'est `tools/build_docs.py` qui calcule la matrice. Ce skill décrit la
**spec** que le script doit respecter. Si tu modifies la matrice, modifie
aussi le build pour qu'ils restent alignés.
