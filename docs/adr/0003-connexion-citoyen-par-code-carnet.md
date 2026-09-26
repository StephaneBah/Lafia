# 0003. Citoyen sign-in with NPI and code carnet

- Status: accepted
- Date: 2026-09-25

## Context

The NPI is not a secret: relatives, employers and neighbours know it. With the NPI alone, anyone could read someone else's carnet. SMS codes need a phone number per person, while many citizens share one phone within the family, and SMS is out of v1.

## Decision

- The citoyen signs in with **NPI plus code carnet**: a short code (6 characters, same unambiguous alphabet as the numéro d'ordonnance) printed on the receipt handed over at each visite.
- `identite` stores the code hashed, against the NPI, and issues a short-lived `citoyen` token scoped to that NPI. It stores no medical data.
- The `citoyen` service returns only the carnet and access log of the token's NPI.

## Consequences

- A citoyen with no visite since Lafia went live has no code, which is acceptable: they have no carnet yet either.
- A lost receipt means no carnet access until the next visite; the paper and the code travel together, as the paper booklet does today.
- How a code is issued, and that a new code replaces the previous one: ADR 0005.
- Rejected: NPI alone (anyone reads anyone's carnet); SMS one-time code (phone numbers, shared phones, out of v1).
