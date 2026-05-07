# Software Design Specification (SDS)

_Généré le 2026-05-07_

## SDS-EXAMPLE-001 — Exemple — module auth/oauth

**Statut :** Draft · **Version :** 1.0.0
**Module :** `src/auth/oauth`
**Implémente :** SRS-EXAMPLE-001
**Mitige :** RSK-EXAMPLE-001, THR-EXAMPLE-001
**Source :** `src/auth/oauth.ts`

## Responsabilité

Gère le handshake OAuth2 Authorization Code + PKCE et la création de la
session signée à l'issue du callback.

## Interfaces

### Entrées
- `GET /auth/login` — sans cookie de session.
- `GET /auth/callback?code=...&state=...` — retour IdP.

### Sorties
- 302 vers `${IDP_URL}/authorize` avec paramètres OAuth2 + PKCE.
- Cookie `sid` HttpOnly + Secure + SameSite=Lax.

### Dépendances
- `openid-client`
- `jose` pour la vérification JWT

## Invariants

- `state` est généré cryptographiquement et lié au sid pré-session.
- Aucun token IdP n'est stocké côté client.

## Notes de design

PKCE imposé même quand le client est confidentiel — défense en profondeur.

---
