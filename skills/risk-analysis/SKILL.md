---
name: risk-analysis
description: Référence ISO 14971 + IEC 62304 §7 pour l'analyse de risques logicielle (Classe A). À invoquer pour identifier les dangers, dériver les contrôles, et produire des items RSK et des exigences SRS de mitigation.
---

# Risk analysis — référence

Applique **ISO 14971:2019** (gestion des risques dispositif médical) et
**IEC 62304 §7** au logiciel Classe A. En Classe A, l'analyse sert
principalement à **justifier la classification** : tous les dangers
identifiés doivent être soit acceptables tels quels, soit réduits à
acceptables par des contrôles.

## Vocabulaire (ISO 14971)

- **Hazard** — source potentielle de dommage.
- **Hazardous situation** — circonstance d'exposition au danger.
- **Harm** — dommage physique, sanitaire, ou atteinte aux données.
- **Risk** — sévérité × probabilité.
- **Risk control / mitigation** — mesure réduisant le risque.

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

### Niveau de risque
Trois niveaux : `Low` / `Medium` / `High`. Tout `High` ou `Medium` non
réductible remet en cause la Classe A.

## Hiérarchie des contrôles (ISO 14971 §7.1)

Toujours dans cet ordre :

1. **Sécurité par conception** — éliminer le danger (p. ex. ne pas
   stocker de secret côté client).
2. **Mesures de protection** dans le logiciel (validation des entrées,
   timeouts, sandboxing, retry borné).
3. **Information de sécurité** — documenter la limite (note README,
   message d'erreur explicite).

Préférer 1 > 2 > 3.

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

## Critère d'acceptabilité

Un RSK est **traité** si l'une des deux conditions tient :

- `risk_level: Low` ET `acceptable: true` (avant mitigation), OU
- au moins un item le mitige ET `residual_acceptable: true` (après
  mitigation, avec contrôles implémentés et vérifiés).

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

Voir skill `items-store` pour les champs communs. Champs spécifiques
RSK : `hazard`, `hazardous_situation`, `harm`, `severity`,
`probability`, `risk_level`, `acceptable`, `residual_acceptable`.

## Note Classe A

Si un risque a `severity: Critical` ou `Catastrophic` après tentative
de mitigation : **arrêter et alerter** — le produit n'est plus Classe A.
Insérer un `[GAP-62304]` explicite et demander à l'utilisateur de
revoir la classification.
