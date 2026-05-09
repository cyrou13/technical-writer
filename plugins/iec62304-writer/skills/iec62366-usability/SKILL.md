---
name: iec62366-usability
description: Référence IEC 62366-1 (usability engineering pour dispositifs médicaux). À invoquer pour produire des Use Scenarios (USC), des Use-Related Risks (URSK) et des tests d'usability (TC type Usability).
---

# IEC 62366-1 — Usability Engineering

## Cadre

- **IEC 62366-1:2015 +A1:2020** — Application of usability engineering
  to medical devices.
- **IEC 62366-2** — Guidance (informative).
- Complémentaire à IEC 62304 (logiciel) et ISO 14971 (risques) : couvre
  spécifiquement les **erreurs d'usage** par l'utilisateur final.

## Vocabulaire

- **Use specification** — qui, où, pour quoi (intended use, profil
  utilisateur, environnement, fréquence).
- **Use scenario** — séquence d'actions normale d'un utilisateur pour
  accomplir une tâche.
- **Use error** — action ou inaction utilisateur qui produit un
  résultat différent de l'intention du fabricant ou de l'utilisateur.
- **Hazard-related use scenario** — use scenario dans lequel une use
  error conduit à un hazard (et potentiellement un harm).
- **Formative evaluation** — testing pendant le design, itératif, vise
  l'amélioration.
- **Summative evaluation** — testing final pour valider la sécurité
  d'usage avant release.

## Catégories d'items

### USC — Use Scenarios
Décrit qui fait quoi, où, comment. Source de vérité pour le contexte
d'usage. Schéma frontmatter dans `items-store`.

### URSK — Use-Related Risks
Erreurs d'usage qui peuvent conduire à un hazard. **Distinctes des RSK
techniques** (origine code) et des THR cyber (origine attaquant).
Origine d'un URSK : l'utilisateur lui-même, par erreur, distraction ou
mauvaise compréhension.

Quand un URSK déclenche un hazard safety (RSK), poser
`links.triggers: [RSK-XXX]` — comme pour un THR.

### TC type Usability
Cas de test d'usability. Champ `usability_type` ∈ {`formative`,
`summative`} pour distinguer.

## Méthode (à appliquer dans l'agent `usability-analyst`)

1. **Identifier les surfaces d'UI** depuis la code-map :
   - Composants UI : `*.tsx`, `*.jsx`, `*.vue`, `*.svelte`,
     templates Angular.
   - Pages / routes : Next.js pages, React Router, Angular Router,
     Vue Router.
   - Formulaires, dialogs, modals (grep `<form`, `<dialog`, `modal`).
   - États d'erreur, alertes, toasts, banners.
   - Raccourcis clavier, drag-and-drop, gestes tactiles.

### Catalogue de patterns UI → SRS frontend → TC E2E

Cette table cadre l'extraction par l'agent `usability-analyst`. Elle
produit des SRS de domaine `VIEWER` (ou nom du composant UI), distincts
des SRS backend produits par `requirements-writer`.

| Source à scanner | SRS produit | Domaine TC E2E |
|---|---|---|
| `<Route path="...">`, route guards, navigation programmatique | `SRS-VIEWER-NAV-*` | Playwright permissions + navigation |
| `<TextField required pattern>`, schémas Yup/Zod côté front, `useForm` | `SRS-VIEWER-FORM-*` | Playwright form-validation |
| `<Dialog>` confirmation patterns, `confirm()`, double-action | `SRS-VIEWER-CONFIRM-*` | Playwright confirmations |
| Flows auth UI : login form, logout button, force password modal, `mustChangePassword` guard | `SRS-VIEWER-AUTH-*` | Playwright auth |
| Loading skeletons, empty state components, error banners | `SRS-VIEWER-STATE-*` | Playwright error-states |
| Permission guards UI : `if (!user.has(...))`, conditional render | `SRS-VIEWER-PERM-*` | Playwright permission boundary |
| WebSocket subscriptions UI (live updates, reconnect logic) | `SRS-VIEWER-WS-*` | Playwright websocket |
| Accessibility : `aria-*`, keyboard navigation, focus management | `SRS-VIEWER-A11Y-*` | axe-core, Playwright a11y |

Pour chaque pattern détecté, l'agent crée :
- 1 ou plusieurs **SRS-VIEWER-***  (exigence UI fonctionnelle observable),
- 1 ou plusieurs **USC** si la séquence d'usage est non-triviale,
- 1 ou plusieurs **URSK** si une use error a un impact patient/données,
- 1 ou plusieurs **TC type E2E** liés (`links.verifies` vers SRS,
  optionnel `links.mitigates` vers URSK).

Si des specs Playwright/Cypress existent déjà dans le repo
(`tests/e2e/`, `e2e/`, `cypress/`), l'agent les détecte et crée des
TC qui pointent dessus via `test_id:` plutôt que de les recréer.

2. **Établir les personas** depuis CLAUDE.md / README / contexte
   produit. Si non explicite → demander à l'utilisateur, ne pas
   inventer.

3. **Produire les USC** par tâche utilisateur identifiable :
   - 1 tâche métier complète = 1 USC.
   - Frontmatter : `persona`, `environment`, `task`, `frequency`,
     `criticality`.
   - Corps : pré-conditions, séquence normale, erreurs possibles
     informelles (celles avec impact deviennent des URSK).

4. **Dériver les use errors plausibles** par USC :
   - Sélection de la mauvaise option par défaut.
   - Validation rapide sans vérification.
   - Confusion entre 2 actions similaires (libellés proches, icônes
     ambiguës).
   - Erreur de saisie (typo, unités, ordre de grandeur).
   - Mauvaise interprétation d'une visualisation
     (couleur/échelle ambiguës).
   - Action irréversible sans confirmation suffisante.
   - Erreur de contexte (multi-patient, multi-fenêtre).

5. **Pour chaque use error** : évaluer si elle peut causer un harm.
   - Si oui → créer un URSK.
   - Sinon → mentionner dans les notes du USC, ne pas créer d'URSK.

6. **Pour chaque URSK** dériver des contrôles UI dans la hiérarchie
   ISO 14971 :
   1. **Élimination par conception** — supprimer le path qui mène à
      l'erreur (ex. retirer la modale ambiguë).
   2. **Mesure technique** — confirmation, double-validation,
      contrainte de saisie, désactivation conditionnelle.
   3. **Information utilisateur** — message, label, hint texte,
      formation.

   Préférer 1 > 2 > 3.

7. **Linkage** :
   - `URSK.links.triggers: [RSK-XXX]` quand l'erreur déclenche un
     hazard safety déjà identifié par le risk-analyst.
   - SRS de mitigation (`priority: Must`,
     `links.mitigates: [URSK-XXX]`) — comme pour RSK / THR.
   - TC type Usability (`links.verifies: [SRS-XXX]` et/ou
     `links.mitigates: [URSK-XXX]`).

## Échelles

Mêmes que ISO 14971 :
- `severity` : Negligible / Minor / Serious / Critical / Catastrophic
- `likelihood` : Improbable / Remote / Occasional / Probable / Frequent
- `risk_level` : Low / Medium / High

## Validation summative

L'IEC 62366-1 attend une **summative evaluation** documentée avant
release. Dans le pipeline :

- TC `type: Usability` + `usability_type: summative`.
- Le STD §3 (stratégie) doit mentionner la stratégie d'évaluation
  (méthode, taille échantillon, critères pass/fail).
- Le rapport summatif lui-même n'est pas auto-généré (c'est de
  l'observation humaine) — l'utilisateur le rédige et l'inclut
  comme artefact dans `docs/usability_summative_report.md` (référencé
  par le STD).

## Garde-fous

- **Pas d'invention de personas** : si le contexte ne les définit pas,
  alerter et demander, pas inventer.
- **Pas de USC sans composant UI réel** : un USC doit pouvoir pointer
  un fichier UI dans `source:`.
- **Pas de URSK sans use error inférable** depuis un USC ou un
  composant.
- **Pas de duplication avec RSK / THR** : la distinction est l'origine
  (utilisateur vs système vs attaquant). Si un hazard est déjà en RSK,
  l'URSK qui pointe la même use error utilise `links.triggers:
  [RSK-XXX]` plutôt qu'une duplication.
- **Pas de scan actif** (pas de Selenium, pas d'instrumentation UI
  runtime).
- Si le projet n'a aucune UI (pas de composants frontend) → l'agent
  produit un rapport vide et explicite "pas de surface UI détectée,
  62366-1 non applicable".

## Note Classe A

Même en Classe A (pas de harm patient direct), une UI clinique
*peut* induire des erreurs avec impact (mauvaise lecture, mauvais
ordre de priorité). 62366-1 reste applicable dès qu'il y a UI
utilisateur. La sévérité des URSK reste cohérente avec la classe :
si un URSK arrive à `severity: Critical/Catastrophic`, la
classification Class A est probablement à revoir.
