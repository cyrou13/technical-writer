---
name: risk-analysis
description: Référence ISO 14971 + IEC 62304 §7 pour l'analyse de risques logicielle (Classe A). À invoquer pour identifier les dangers, dériver les contrôles, et produire des items RSK et des exigences SRS de mitigation.
---

## OUTPUT LANGUAGE — STRICT

Any artifact produced while applying this skill (RSK items, derived
SRS, frontmatter values, body sections, `[GAP-62304]` markers) MUST be
written in **English**, regardless of the user's conversational
language or any global `CLAUDE.md` instruction.

# Risk analysis — référence

Applique **ISO 14971:2019** (gestion des risques dispositif médical) et
**IEC 62304 §7** au logiciel Classe A. En Classe A, l'analyse sert
principalement à **justifier la classification** : tous les dangers
identifiés doivent être soit acceptables tels quels, soit réduits à
acceptables par des contrôles.

## Vocabulaire (ISO 14971)

- **Hazard** — source potentielle de dommage.
- **Initiating cause** — déclencheur indépendant qui peut amorcer la
  séquence (ISO 14971 §C.2). Un même hazard peut avoir plusieurs causes.
- **Foreseeable sequence of events** — chaîne `(1) → (2) → ... →
  hazardous situation`. Sans cette chaîne explicite, l'item n'est pas
  conforme ISO 14971 §C.2.
- **Hazardous situation** — circonstance d'exposition au danger.
- **Harm** — dommage physique, sanitaire, ou atteinte aux données.
- **Risk** — sévérité × probabilité (`P × S`, index numérique).
- **Risk level (RL)** — projection qualitative de l'index sur
  `Low / Medium / High` via une matrice d'acceptabilité.
- **Risk control / mitigation** — mesure réduisant le risque.
- **Arising risk** — risque NOUVELLEMENT créé par une mitigation
  (ISO 14971 §7.5). Doit être tracé dans `arising_risks` de l'item parent.

## Chaîne causale (ISO 14971 §C.2 — obligatoire)

Chaque RSK doit documenter explicitement les **4 maillons** :

```
initiating causes  →  foreseeable sequence of events  →  hazardous situation  →  harm
   (déclencheurs)        (chaîne d'événements)              (exposition)         (dommage)
```

Un RSK qui n'a que `hazard` + `harm` est **incomplet** (ISO 14971 §C.2.2).
L'agent doit remplir les 4 champs, quitte à mettre `[TODO]` quand le code
seul ne permet pas de dériver la chaîne complète (input clinique requis).

## Catégories typiques de hazards logiciels

1. **Erreur fonctionnelle** — calcul faux, état incohérent.
2. **Défaillance** — crash, deadlock, fuite mémoire, OOM, timeout.
3. **Sécurité** — injection, XSS, CSRF, fuite de secret, escalade.
4. **Intégrité des données** — corruption, perte, désynchronisation.
5. **Auth/Autz** — bypass, élévation de privilège, session fixée.
6. **Confidentialité** — exposition de données sensibles, logs PII.
7. **Disponibilité** — indisponibilité prolongée, dégradation silencieuse.
8. **Usabilité** — interface induisant en erreur (rare en Classe A).

## Échelles (Class A — simplifiées)

### Sévérité
| Niveau | Définition |
|---|---|
| Negligible | Inconfort utilisateur transient, sans suite |
| Minor | Perte de données récupérable, désagrément |
| Serious | Atteinte durable (vie privée, financier) |
| Critical | NA Classe A — déclenche reclassement B/C |
| Catastrophic | NA Classe A |

### Probabilité (optionnelle Classe A)
`Improbable` / `Remote` / `Occasional` / `Probable` / `Frequent`.

### Mapping numérique (pour le calcul P × S)

| Severity     | Int | Probability  | Int |
|---|---|---|---|
| Negligible   | 1   | Improbable   | 1   |
| Minor        | 2   | Remote       | 2   |
| Serious      | 3   | Occasional   | 3   |
| Critical     | 4   | Probable     | 4   |
| Catastrophic | 5   | Frequent     | 5   |

Index numérique = `severity_int × probability_int` ∈ [1, 25].

### Niveau de risque (Risk Level)

Matrice par défaut (ISO 14971 §C.5, adaptée Classe A) :

| Index | Risk Level |
|---|---|
| 1 – 4   | Low    |
| 5 – 12  | Medium |
| 13 – 25 | High   |

Tout `High` ou `Medium` non réductible remet en cause la Classe A.
La matrice peut être surchargée par l'utilisateur via `dt-config.yaml`
(à venir) ou en éditant l'item au cas par cas avec justification dans
`## Initial risk justification`.

## Hiérarchie des contrôles (ISO 14971 §7.2 — obligatoire)

Chaque RSK doit déclarer son `control_hierarchy` parmi les 3 niveaux,
dans l'ordre de préférence imposé par ISO 14971 :

1. **`inherent_design`** — éliminer le danger au design time. Premier
   choix. P. ex. ne pas stocker de secret côté client ; utiliser un
   générateur cryptographique pour les nonces.
2. **`protective_measure`** — barrière dans le logiciel qui empêche le
   harm de se matérialiser. P. ex. validation d'entrée, timeout,
   sandboxing, retry borné.
3. **`information_for_safety`** — informer l'utilisateur dans l'IFU /
   le labeling / un message UI. Dernier recours.

L'agent doit choisir le niveau le plus haut **praticable** et justifier
dans `## Risk controls` pourquoi un niveau supérieur n'est pas atteignable
(p. ex. exigence MAP impose OAuth2 → on ne peut pas éliminer la
fonctionnalité, donc descente à `protective_measure` ou `inherent_design`
du sous-élément).

Si `control_hierarchy: information_for_safety`, alors `labeling_disclosure`
**doit** contenir le texte verbatim à inclure dans l'IFU (sinon
`[GAP-62304]`).

## Forme d'une mitigation

Trois formes possibles, **toujours liées à RSK via `links.mitigates`** :

- **SRS de mitigation** — exigence fonctionnelle de protection. Item SRS
  classique, `priority: Must`, `links.mitigates: [RSK-XXX]`.
  → Apparaît dans `_to_implement.md` tant qu'aucun SDS ne l'implémente
  ni TC ne la vérifie.
- **Contrainte SDS** — décision de design (isolation, no-secret-in-state).
  Item SDS avec `links.mitigates`.
- **TC dédié** — preuve d'efficacité (test de non-régression). Item TC
  avec `links.mitigates`.

Un même item peut mitiger plusieurs RSK (liste dans `mitigates`).

## Résidual quantitatif (ISO 14971 §7.4 — obligatoire)

Après application des contrôles, l'agent doit re-évaluer **quantitativement** :

- `residual_probability` ∈ {Improbable, Remote, Occasional, Probable, Frequent}
- `residual_severity` ∈ {Negligible, Minor, Serious, Critical, Catastrophic}
- `residual_risk_level` = projection de `residual_p × residual_s` sur la matrice
- `residual_acceptable` = bool (Low → true en Classe A typique)

L'agent rédige `## Residual risk justification` qui explique pourquoi
chaque dimension a baissé (ou non — pour les contrôles SW, seule la
probabilité baisse en général, la sévérité reste).

## Arising risks (ISO 14971 §7.5 — obligatoire)

Si la mitigation **crée** un nouveau risque (par exemple : ajouter un
filtre de rejet crée un risque de faux négatif clinique), l'agent doit :

1. Créer un nouvel item `RSK-XXX-NNN` pour ce nouveau risque
2. Ajouter son ID dans `arising_risks` de l'item parent

`arising_risks` est une liste d'IDs, par défaut vide.

## Critère d'acceptabilité

Un RSK est **traité** si l'une des deux conditions tient :

- `risk_level: Low` ET `acceptable: true` (avant mitigation, contrôle
  par construction), OU
- au moins un item le mitige ET `residual_risk_level: Low` ET
  `residual_acceptable: true` ET tous les `arising_risks` sont
  eux-mêmes traités.

Tout RSK ne satisfaisant pas ces critères apparaît dans
`_to_implement.md`.

## Méthode d'identification (à appliquer dans l'agent)

Parcourir le codemap et systématiquement chercher :

1. **Points d'entrée externes** — chaque route HTTP, chaque commande
   CLI : quels inputs malicieux ?
2. **Frontières de confiance** — appels externes, fichiers utilisateur,
   variables d'environnement.
3. **Stockage de secrets** — clés, tokens, mots de passe.
4. **Persistance** — corruption, race conditions, transactions
   incomplètes.
5. **Calculs sensibles** — montant, dosage, identifiant — si pertinents.
6. **Logs & télémétrie** — fuite PII potentielle.

Pour chaque candidat, formuler `hazard` / `hazardous_situation` / `harm`
en phrases courtes et factuelles. **Ne pas inventer** de dangers
théoriques sans rattachement au code.

## Schéma RSK

Voir skill `items-store` pour les champs communs. Champs spécifiques RSK :

| Champ | Type | Obligatoire | Notes |
|---|---|---|---|
| `risk_category` | enum | oui | Design \| Production \| Usability |
| `software_function` | string | oui | Fonction métier où le risque émerge |
| `software_item` | string | oui | Module / fichier responsable |
| `hazard` | string | oui | ISO 14971 §3.2 |
| `initiating_causes` | block list | oui | ISO 14971 §C.2 — chaîne causale |
| `foreseeable_sequence` | block scalar | oui | ISO 14971 §C.2 — `(1) → (2) → ...` |
| `hazardous_situation` | string | oui | |
| `harm` | string | oui | |
| `severity` | enum | oui | Negligible..Catastrophic |
| `probability` | enum | oui | Improbable..Frequent |
| `risk_level` | enum | oui | Low \| Medium \| High (matrice) |
| `acceptable` | bool | oui | Avant mitigation |
| `control_hierarchy` | enum | oui | inherent_design \| protective_measure \| information_for_safety |
| `residual_probability` | enum | oui | Re-évaluation post-mitigation |
| `residual_severity` | enum | oui | Re-évaluation post-mitigation |
| `residual_risk_level` | enum | oui | Re-projection sur la matrice |
| `residual_acceptable` | bool | oui | Après mitigation |
| `arising_risks` | list[ID] | défaut `[]` | IDs RSK créés par la mitigation |
| `labeling_disclosure` | string \| null | oui si `control_hierarchy=information_for_safety` | Texte IFU verbatim |

## Note Classe A

Si un risque a `severity: Critical` ou `Catastrophic` après tentative
de mitigation : **arrêter et alerter** — le produit n'est plus Classe A.
Insérer un `[GAP-62304]` explicite et demander à l'utilisateur de
revoir la classification.
