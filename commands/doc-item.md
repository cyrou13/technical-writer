---
description: Crée ou met à jour un item de documentation (SRS/SDS/TC/RSK) avec frontmatter conforme. Usage — /doc-item SRS-AUTH-001 [titre]
---

L'utilisateur veut créer ou éditer **un seul** item de documentation.

`$ARGUMENTS` est attendu sous la forme : `<ID> [titre éventuel]`.

## Étapes

1. Parser l'argument :
   - extraire `ID` (forme `<CAT>-<DOMAIN>-<NNN>`),
   - le reste = titre éventuel.

2. Si `ID` mal formé → expliquer le format à l'utilisateur (cf. skill
   `items-store`) et s'arrêter.

3. Déterminer la catégorie depuis le préfixe (`SRS`, `SDS`, `TC`, `RSK`).

4. Cible : `docs/items/<CAT>/<ID>.md`.

5. Si le fichier existe → l'ouvrir en lecture, proposer la modification
   demandée à l'utilisateur, appliquer en respectant les règles
   d'idempotence (`items-store`).

6. Sinon, **créer** en partant du template
   `docs/templates/<cat-lower>-item.template.md` et préremplir :
   - `id`, `title`, `created`, `updated` (date du jour),
   - `version: 1.0.0`, `status: Draft`,
   - `source:`, `links:` vides,
   - corps : sections du template, `[TODO]` partout où l'utilisateur
     doit compléter.

7. Afficher le chemin créé et les sections à compléter.

## Règles

- Ne JAMAIS réutiliser un ID déjà attribué (même si le fichier a été
  supprimé). Vérifier dans tout `docs/items/` qu'aucun item n'a cet ID
  en frontmatter.
- Ne pas créer le dossier de catégorie sans confirmation si la catégorie
  n'existe pas encore (ex. première fois qu'on crée un RSK).
