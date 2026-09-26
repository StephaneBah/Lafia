# 0006. Code and identifier systems in the noyau

- Status: accepted
- Date: 2026-09-26

## Context

Every code and identifier in a FHIR resource names the system it belongs to. The noyau holds codes Lafia defines (the type of an `Organization`, an agent's role, a product of the catalogue) and one identifier Lafia composes (a tarif's). Services search the noyau by these systems, and resources written by later features will carry them, so renaming one means rewriting what the noyau holds.

## Decision

- **Lafia's own systems are named under `https://lafia.bj/fhir`**, in `commun/src/commun/fhir/systemes.py`, which every service and the loader import:

  | System | Names |
  |---|---|
  | `…/CodeSystem/type-de-structure` | what an `Organization` is: `chu-national`, `chu-departemental`, `chu-de-zone`, `centre-de-sante`, `officine` |
  | `…/CodeSystem/role` | an agent's role, the `qualification` of its `Practitioner`: the token roles |
  | `…/CodeSystem/catalogue` | the products and acts an ordonnance can carry: `MED-PARACETAMOL-500`, `ACT-CONSULTATION`, `EXA-NFS` |
  | `…/identifiant/tarif` | a tarif, as `<établissement id>:<product code>` |

  These URLs are names, not addresses: nothing is served there.
- **A tarif is found in one search**: `ChargeItemDefinition?identifier=https://lafia.bj/fhir/identifiant/tarif|<établissement>:<code>`. The établissement's reference also sits in `useContext`, but R4 offers no search on a `useContext` reference.
- **Standard systems where one exists**: the NPI (`https://npi.gouv.bj`, invariant 6), ATC for medicines, ISO 3166 for countries, BCP 47 for languages, HL7 v2 table 0131 for the personne à prévenir, HL7 `usage-context-type` for the `venue`.

## Consequences

- A service finds what it needs by exact code or identifier, with no project rule inside HAPI.
- Until services write resources of their own (F3), the loader rewrites every dataset resource with a new system on its next run: renaming is cheap now and costly after.
- An établissement's id is part of every one of its tarif identifiers: it cannot change without new tarifs.
- Rejected: one `ChargeItemDefinition` per product carrying every établissement's price (the caisse would search a product, then pick a price by hand); searching tarifs by `useContext` (not searchable on a reference in R4); systems under the deployment's domain (it names a machine, and would change with it).
