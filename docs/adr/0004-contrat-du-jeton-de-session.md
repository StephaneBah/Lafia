# 0004. Session token contract

- Status: accepted
- Date: 2026-09-26

## Context

`identite` issues the tokens that every service verifies on its own (`commun/src/commun/jeton.py`), without calling `identite`. Their shape binds `identite`, every service, every application and the test suite, so it is costly to change once they rely on it.

## Decision

- **Signature**: EdDSA, Ed25519. Only `identite` holds the private key (`JETON_CLE_PRIVEE`); services hold the public key (`JETON_CLE_PUBLIQUE`). Without keys, on `localhost` only, both sides use the development pair, whose private half is public; on any other domain they refuse to start without a key, and refuse the development key.
- **Claims**, by kind of holder, plus `exp` for all. Any other shape is refused with 401.

  | Holder | `sub` | `role` | Other claim |
  |---|---|---|---|
  | Agent | the agent's `Practitioner` id in the noyau | `médecin`, `infirmier`, `caissier`, `pharmacien` | `etablissement`: the `Organization` id of their établissement |
  | Officine | the officine's `Organization` id | `officine` | none |
  | Citoyen | drawn at random at each sign-in, never derived from the NPI | `citoyen` | `npi` |

- **Lifetime**: a token lives 15 minutes; services refuse one that expires more than an hour ahead. `identite` also keeps a session, named by a second `__Host-` cookie, from which the application renews the token: at most 12 hours, and 30 minutes idle, for agents and officines; at most one hour for the citoyen. Déconnexion ends the session.
- **Transport**: `identite` sets the token in the `__Host-session` cookie, `httpOnly`, `Secure`, `SameSite=Strict`, on the subdomain of the application where the sign-in happened, and never returns it in a response body. Services also accept it in an `Authorization: Bearer` header, for clients that are not browsers: the test suite, future integrators.
- **One role, one application**: `identite` signs a role in only on the application that serves it: médecin and infirmier on soin, caissier on caisse, pharmacien and officine on pharmacie, citoyen on citoyen.

## Consequences

- Services write `Practitioner/<sub>` as the author of a write, and as the agent of an `AuditEvent`, without asking `identite`.
- An officine signs in under its own name, and its reach comes from its role alone: its token names no établissement, since an officine is not one.
- A token stays valid up to 15 minutes after déconnexion.
- The test suite gets valid tokens by signing in through `identite` with demo accounts. Tokens of a wrong shape can only be forged with the development key, so those tests run locally only.
- Rejected: the NPI as the citoyen's `sub` (the application would learn it, against F1.6); one token for a whole shift (services cap tokens at one hour, and déconnexion would end nothing); the role `pharmacien` with the officine as établissement (reach would depend on reading the noyau instead of the signed token, and an officine is not an établissement).
