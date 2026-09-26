# 0005. Code carnet issued through the application soin

- Status: accepted
- Date: 2026-09-26

## Context

ADR 0003 has `identite` store each code carnet hashed against the NPI, and left open whether a new code revokes the previous one. The code is printed on the reçu at the end of a visite, and the visite happens in `soin`. But `soin` cannot call `identite`, since services never call each other, and `identite` cannot see the visite: it never speaks FHIR and is not on the noyau's network.

## Decision

- At the end of each visite, the **application soin**, which may call `identite`, asks it for a code with the soignant's session and the patient's NPI. `identite` admits médecin and infirmier, draws the code, stores its hash against the NPI together with who asked (agent, établissement, time), and returns the code once, to be printed on the reçu.
- **One valid code per NPI.** Each new code replaces the previous one; a code has no other expiry. The citoyen uses the code on their latest reçu.

## Consequences

- `identite` cannot check the relation de soin. A soignant could obtain a code for any NPI and open that person's carnet without an accès d'urgence. Accepted for v1, and limited three ways: every code is recorded with the agent who asked for it; the citoyen's own reçu stops working, which they notice; sign-in attempts are rate-limited.
- A lost reçu means no carnet until the next visite, as in ADR 0003.
- Rejected: `identite` reads the noyau to check for an open cas (reverses the F1 topology, and `identite` would handle medical data); `soin` signs an attestation de visite with a key of its own for `identite` to verify (a second signing key and its machinery, for v1); several valid codes with an expiry (old reçus stay usable, and a code obtained by someone else goes unnoticed).
