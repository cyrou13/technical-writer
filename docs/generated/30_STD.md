# Software Test Description (STD)

_Class A · IEC 62304 §5.5/§5.7 · IEEE 829 · Généré le 2026-05-07_

## 1. Introduction

### 1.1 Objet

Ce document décrit l'environnement, la stratégie et les cas de test
pour la vérification du logiciel selon IEC 62304 §5.5 (vérification
unitaire) et §5.7 (test système). Les cas de test sont produits depuis
`docs/items/TC/` ; ce STD est régénéré à chaque build.

### 1.2 Documents de référence

- SRS — `docs/generated/10_SRS.md`
- SDS — `docs/generated/20_SDS.md`
- Matrice de traçabilité — `docs/generated/40_traceability.md`
- Analyse de risques (safety) — `docs/generated/50_risk_analysis.md`
- Analyse cyber — `docs/generated/60_cyber_risk_analysis.md`
- IEC 62304:2006/AMD1:2015
- IEEE 829-2008 (Standard for Software and System Test Documentation)

### 1.3 Niveaux de test couverts

- **Unit** — 0 TC
- **Integration** — 1 TC
- **System** — 0 TC

## 2. Environnement de test

_Aucun framework de test détecté automatiquement. Compléter via `docs/test_plan_intro.md`._

## 3. Stratégie de test

[TODO Décrire la stratégie de test :

- niveaux ciblés (unit / intégration / système / E2E),
- méthode (TDD/BDD/test-after, exigence de couverture),
- outillage (Vitest/Jest, pytest, Playwright/Cypress…),
- fréquence et déclencheurs (pre-commit, CI sur PR, nightly),
- périmètre de l'automatisation vs tests manuels,
- gestion des fixtures et données de test.]

## 4. Critères de pass/fail

- **PASS** — tous les TC vérifiant un SRS `priority: Must` sont
  exécutés et passants ; aucun TC orphelin (sans `verifies`).
- **FAIL** — ≥ 1 TC vérifiant un SRS Must est en échec.
- **Skipped** — tracé dans le rapport, ne compte pas comme pass.

## 5. Couverture

| Niveau | # TC | SRS Must couverts |
|---|---|---|
| Unit | 0 | 0/1 (0%) |
| Integration | 1 | 1/1 (100%) |
| System | 0 | 0/1 (0%) |

## 6. Cas de test

### 6.1 Integration

| ID | Titre | Vérifie | Auto |
|---|---|---|---|
| TC-EXAMPLE-001 | Exemple — login redirige vers l'IdP avec state et PKCE | SRS-EXAMPLE-001 | True |

## 7. Exclusions

[TODO Lister ce qui n'est PAS testé en automatique et pourquoi :

- composants tiers traités en boîte noire (avec justification),
- environnements non couverts (mobile, navigateurs anciens…),
- scénarios de charge / performance hors périmètre v1,
- tests d'accessibilité reportés.]

---

# Annexe A — Détail des cas de test

## TC-EXAMPLE-001 — Exemple — login redirige vers l'IdP avec state et PKCE

**Statut :** Draft · **Version :** 1.0.0
**Type :** Integration · **Auto :** True
**Vérifie :** SRS-EXAMPLE-001
**Mitige :** RSK-EXAMPLE-001, THR-EXAMPLE-001
**Source :** `src/auth/oauth.test.ts`

## Préconditions

- IdP de test (mock) démarré sur `http://localhost:9000`.
- Variables d'env `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET` chargées.

## Étapes

1. Effectuer `GET /auth/login` sans cookie.
2. Récupérer la réponse HTTP.

## Résultats attendus

- Code 302.
- En-tête `Location` pointant `http://localhost:9000/authorize`.
- Query string contient `client_id`, `redirect_uri`, `state` (≥ 32
  caractères), `code_challenge`, `code_challenge_method=S256`.

## Notes

Item exemple. À supprimer ou remplacer.

---
