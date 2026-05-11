---
name: prompts-generator
description: Génère des prompts ready-to-paste à fournir à d'autres sessions Claude Code pour combler les gaps de couverture identifiés par `/doc-build` — code manquant (SRS sans SDS), tests unitaires (SRS sans TC), tests E2E Playwright (SRS surface UI). Un fichier prompt par SRS orphelin sous `docs/generated/prompts/`. À invoquer APRÈS `/doc-build` qui produit `coverage.json` et `_to_implement.md`.
---

## OUTPUT LANGUAGE — STRICT

All generated prompt files MUST be in **English** (they will be pasted
into Claude Code sessions which work best in English).

# Coverage-gap prompts generator

`/doc-build` identifie les SRS orphelins dans `_to_implement.md` :
- **D.1** : SRS Must sans SDS implémentant (code manquant)
- **D.2** : SRS Must sans TC vérifiant (tests manquants)

Ce skill transforme chaque ligne de D.1/D.2 en **fichier prompt
autonome**, prêt à coller dans une session Claude Code ciblée. Plus
de copier-coller manuel — l'utilisateur ouvre le fichier prompt, copie
tout, ouvre une nouvelle session dans le repo cible, colle. Claude
Code prend le relais avec tout le contexte (produit, intended use,
SRS verbatim, contraintes du repo).

## 3 types de prompts par SRS orphelin

| Type | Quand généré | Output attendu de la session Claude |
|---|---|---|
| `<SRS-ID>-impl.md` | SRS sans SDS implémentant | Code de la mitigation + SDS item créé/édité + anchor `@implements SRS-ID` dans le code |
| `<SRS-ID>-unit-tests.md` | SRS sans TC | Tests unitaires (pytest/vitest/jest auto-détecté) + TC item créé + anchor `@verifies SRS-ID` dans le test |
| `<SRS-ID>-e2e.md` | SRS surface UI sans TC | Test Playwright E2E + TC item (`type: System` ou `E2E`) + use scenario respecté |

## Détection UI (heuristiques)

Un SRS est considéré "UI-surfaced" si **au moins une** condition tient :

- `source:` contient `*.tsx` / `*.jsx` / `*.vue` / `*.svelte` ou
  `frontend/` / `ui/` / `web/` / `viewer/`
- Title ou description mentionne `user clicks`, `screen`, `form`,
  `viewer`, `operator`, etc.
- `links.parent` pointe vers un USC (use scenario IEC 62366-1)

Seuls les SRS UI-surfaced reçoivent un prompt E2E supplémentaire.

## Structure d'un prompt généré

Chaque fichier prompt contient :

1. **Header** : ID de l'SRS, date de génération, instruction "paste in
   Claude Code session".
2. **Product context** : tiré de `dt-config.yaml` + intended-use de
   `dt-clinical-context.md`.
3. **SRS verbatim** : title, description, verification, priority,
   source, full body Markdown. Pas d'interprétation — Claude Code
   reçoit l'item brut.
4. **Use scenario** (E2E uniquement) : persona / environment / task
   tirés du USC parent si présent.
5. **Task** : 4-6 étapes ordonnées (identifier le module / écrire le
   code / créer le SDS-TC item / ajouter l'anchor / runner tests).
6. **Constraints** : conventions du repo, lint, frameworks, pas de
   nouvelle dépendance sans accord, stabilité de l'API publique.
7. **References** : templates à utiliser, format d'ID, commandes
   plugin à relancer après.

## Catalogue

`docs/generated/prompts/_index.md` répertorie tous les prompts générés
avec liens cliquables et compteurs. C'est l'entry point.

## Inputs

| Source | Obligatoire | Si absent |
|---|---|---|
| `docs/items/SRS/*.md` | oui | erreur exit 1 |
| `docs/items/SDS/*.md` | non | tous les SRS considérés orphelins SDS |
| `docs/items/TC/*.md` | non | tous les SRS considérés orphelins TC |
| `docs/items/USC/*.md` | non | détection UI moins fiable (heuristiques sources/text seules) |
| `dt-config.yaml` | non | product context = `[TODO]` |
| `docs/dt-clinical-context.md` | non | intended-use omis du prompt |

## Outputs

| Fichier | Contenu |
|---|---|
| `docs/generated/prompts/_index.md` | Catalogue avec compteurs + liens |
| `docs/generated/prompts/<SRS-ID>-impl.md` | 1 prompt par SRS sans SDS |
| `docs/generated/prompts/<SRS-ID>-unit-tests.md` | 1 prompt par SRS sans TC |
| `docs/generated/prompts/<SRS-ID>-e2e.md` | 1 prompt par SRS UI sans TC |

## CLI

```bash
python tools/build_prompts.py                # tous les prompts
python tools/build_prompts.py --cat impl     # seulement impl
python tools/build_prompts.py --cat unit     # seulement unit-tests
python tools/build_prompts.py --cat e2e      # seulement E2E
python tools/build_prompts.py --srs SRS-X-001  # un seul SRS (debug)
python tools/build_prompts.py --clean        # nettoie le dossier avant
```

## Workflow recommandé

```bash
/iec62304-writer:doc-62304            # pipeline complet
/iec62304-writer:doc-build            # agrégats + coverage
/iec62304-writer:doc-prompts          # génère les prompts pour les gaps

# Pour chaque prompt sous docs/generated/prompts/ :
#   1. cat docs/generated/prompts/<SRS-ID>-impl.md
#   2. Ouvrir une nouvelle session Claude Code dans le repo
#   3. Coller le contenu, laisser tourner
#   4. Reviewer le diff, commit
# Répéter pour unit-tests.md puis e2e.md s'il y en a

# Une fois les gaps comblés :
/iec62304-writer:doc-build            # vérifier que coverage = 100%
/iec62304-writer:doc-prompts --clean  # cleanup (les prompts ne sont plus nécessaires)
```

## Garde-fous

- **Lecture seule** : ne touche jamais aux items existants.
- **Idempotent** : ré-exécuter écrase les prompts précédents
  (--clean pour forcer un cleanup explicite).
- **Pas de fabrication** : si un SRS a une description vide, le prompt
  pointe le body Markdown — l'auteur RAQA doit garantir que les SRS
  sont bien rédigés en amont.
- **Le prompt n'exécute rien** : c'est de la matière première à
  coller dans une autre session. La session cible reste responsable
  de toutes les actions (write, edit, run tests, commit).
