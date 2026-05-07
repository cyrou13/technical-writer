# Plan & preuves de vérification

_Généré le 2026-05-07_

## TC-EXAMPLE-001 — Exemple — login redirige vers l'IdP avec state et PKCE

**Statut :** Draft · **Version :** 1.0.0
**Type :** Integration · **Auto :** True
**Vérifie :** SRS-EXAMPLE-001
**Mitige :** RSK-EXAMPLE-001
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
