---
name: srs-extract
description: Extraire des exigences logicielles (62304 §5.2) depuis du code TypeScript/JavaScript et Python. À invoquer pour générer ou enrichir des items SRS dans docs/items/SRS/.
---

# SRS — extraction d'exigences depuis le code

## Sources d'exigences à scanner

Par ordre de fiabilité décroissante :

1. **Commentaires taggés explicitement**
   - TS/JS : `// @req SRS-AUTH-001 ...` ou `/** @req ... */`
   - Python : `# @req SRS-AUTH-001 ...` ou docstring `:req SRS-AUTH-001:`
   - Si présent → l'ID dans le tag est l'autorité.

2. **API publique**
   - TS : `export function`, `export class`, `export default`, types
     publics dans `index.ts`.
   - Python : fonctions/classes du `__all__`, ou non-préfixées `_` dans
     un module top-level.
   - Routes HTTP : décorateurs FastAPI (`@app.get`), Express
     (`app.get(...)`), Next.js route handlers, NestJS controllers.
   - CLI : `argparse`, `commander`, `yargs`.

3. **Cas d'erreur explicites**
   - Classes d'exception définies + leurs messages → exigences de
     comportement en erreur.
   - `assert` / `invariant` / `zod.parse` → contraintes d'entrée.

4. **Tests** — chaque `describe` / `it` / `test_*` exprime un
   comportement attendu = candidat exigence (mais souvent trop fin →
   regrouper).

5. **Configuration & schémas** — schémas Zod / Pydantic / JSON Schema /
   variables d'environnement requises.

## Heuristique de regroupement

- 1 endpoint REST = 1 SRS (ou plusieurs si méthodes différentes ont des
  sémantiques séparées).
- 1 commande CLI = 1 SRS.
- 1 classe publique avec responsabilité métier claire = 1 SRS.
- N tests qui testent la même règle métier = 1 SRS.

Éviter le sur-découpage : un SRS doit être une **propriété observable du
système**, pas un détail d'implémentation.

## Forme attendue de chaque item SRS

Voir `items-store` pour le schéma complet. Le corps Markdown contient :

```markdown
## Description

Le système **doit** <comportement> quand <condition>, et **doit**
<garantie> dans tous les cas.

## Critères d'acceptation

- [ ] <critère 1, mesurable>
- [ ] <critère 2>

## Notes

<contexte utile, hors normatif>
```

## Anti-patterns à refuser

- "Le système doit être performant" — pas mesurable.
- "Le système doit utiliser PostgreSQL" — c'est du SDS, pas du SRS.
- Reformuler du code en pseudo-code dans la description — décrire le
  *comportement*, pas l'implémentation.

## Sortie

Pour chaque exigence détectée :

1. Vérifier si un item existe déjà avec un `source:` qui pointe le même
   fichier — si oui, **mettre à jour** (cf. règles d'idempotence
   `items-store`), ne pas créer un doublon.
2. Sinon, créer `docs/items/SRS/SRS-<DOMAIN>-<NNN>.md` avec le prochain
   `NNN` libre dans le domaine.
3. Remplir `source:` avec les chemins relatifs depuis la racine du repo.
4. Laisser `links:` vides — le linkage SDS→SRS et TC→SRS sera fait par
   les autres agents.

## Quand il y a doute

Insérer `[TODO]` dans la description et lister la question dans une
section `## Questions ouvertes`. **Ne pas inventer.**
