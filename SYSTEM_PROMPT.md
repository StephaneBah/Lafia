# Lafia: project brief

## Mission

A Beninese citizen's medical memory is scattered: paper booklets that get lost, registers local to each facility, lab results that exist as one physical copy. The patient is the only link between their own carers. Lafia gives every citizen one shared record, reachable by their **NPI** alone, that follows the person across facilities.

The unit of care is the **cas de visite**: a health problem from opening to closure, grouping every visite, mesure, diagnostic, ordonnance and délivrance tied to it. Definitions in `CONTEXT.md`.

## Context

- Benin, 2026. The government programme commits to a digital health record for every Beninese, backed by a hospital information system generalised to all facilities, and to deferred payment for vital emergencies.
- Institutions: ASIN operates the State's shared digital infrastructure; ARS regulates health; the NPI is the civil identifier; ARCH covers vulnerable populations.
- This build answers a three-day challenge. It is judged on depth of usage thinking, design, a working deployed platform, and code quality. Deliverables: a GitHub repository and a live URL.

## Sources of truth

This file and `CONTEXT.md` are canonical. `cahier-des-charges-lafia.html` (functional) and `lafia-document-technique.html` (technical) are the French deliverables for the jury, derived from them; when they disagree, this file wins and the HTML is updated at the end of the session. `prd_for_design.md` governs the design system and interfaces.

## Architecture invariants

The system has three layers: one **noyau**, domain **services** around it, and one **application** per actor on top.

```
app citoyen   app soin   app caisse   app pharmacie      Next.js, one per actor
     │           │           │            │
  citoyen      soin       caisse     pharmacie   identite   FastAPI services
     └───────────┴───────────┴────────────┴──────────┘
                            noyau FHIR
```

1. **Core and services.** The noyau (HAPI FHIR R4, JPA, PostgreSQL) holds all medical data. Domain services (`identite`, `soin`, `caisse`, `pharmacie`, `citoyen`) run as separate containers.
2. **Services speak FHIR to the noyau only.** Services never call each other. `commun/` is a library imported at build time, never a runtime dependency.
3. **HAPI runs in default configuration** and is consumed through its standard REST API. Project rules live in the services.
4. **The noyau is internal.** HAPI publishes no port; the Caddy gateway is the only public entry.
5. **One application per actor.** `web/citoyen`, `web/soin`, `web/caisse`, `web/pharmacie` are separate Next.js apps, each on its own subdomain. An app calls **its own service plus `identite`**, through the gateway, and nothing else. Apps are not on the noyau's network, never speak FHIR and store no medical data. They share two workspace packages, built in, never a runtime dependency: the design system `web/design/`, and `web/commun/`, the application code every app would otherwise repeat, such as reaching its own service through the gateway. `web/commun/` must never open a path around the services: it calls only the app's own service and `identite`, never another actor's service, the noyau or FHIR. A new actor (laboratoire, télémédecine, a third party) joins the same way: its own app, its own service, FHIR to the noyau. See `docs/adr/0001-une-application-par-acteur.md`.
6. **Identity is the NPI**, carried in `Patient.identifier` with system `https://npi.gouv.bj`. Lafia creates no patient identifier of its own.
7. **Only `identite` owns a database**: agent accounts, roles, facility, codes carnet. It stores no medical data.
8. **Records are append-only.** A correction is a new version; history stays readable.
9. **Portable by design.** Docker Compose on one Azure VM; the critical path uses no provider-specific managed service.

## Stack

Python 3.11 and FastAPI for services; Next.js (App Router, TypeScript, standalone output) for the applications, in an npm workspace under `web/`; HAPI FHIR JPA Server and PostgreSQL for the noyau; Caddy as gateway with one subdomain per application; Docker Compose on an Azure Linux VM, with a memory limit on every container.

## FHIR mapping

| Domain term | FHIR resource | Key link |
|---|---|---|
| Patient | `Patient` | NPI in `identifier` |
| Cas de visite | `EpisodeOfCare` | `patient`, `managingOrganization` |
| Visite | `Encounter` | `episodeOfCare`, `participant` |
| Mesure | `Observation` | `encounter`, `effectiveDateTime` |
| Document | `DocumentReference` | `context.encounter` |
| Diagnostic | `Condition` | `encounter`, `verificationStatus` |
| Ligne d'ordonnance | `MedicationRequest` | `groupIdentifier` = numéro d'ordonnance |
| Délivrance | `MedicationDispense` | `authorizingPrescription` |
| Tarif | `ChargeItemDefinition` | product code, price in FCFA |
| Encaissement | `Invoice` | settled lines, deferred-payment flag |
| Allergie | `AllergyIntolerance` | `patient` |
| Soignant | `Practitioner` | author of every write |
| Établissement | `Organization` | where visites happen |
| Accès | `AuditEvent` | `agent`, `entity` |

**Numéro d'ordonnance:** `ORD-` followed by 6 characters in two groups, drawn from an alphabet without ambiguous characters (no `0 O 1 I L`), e.g. `ORD-7K4-M2P`. Readable aloud, typeable without a scanner, printed with a QR code, and always findable by NPI when the receipt is lost.

## Security and health-data statement

A shared national record concentrates the most intimate data a person has. These rules hold in every change:

- **Least privilege by role**, enforced in each service from the signed token:

  | Role | Application and service | Data reach |
  |---|---|---|
  | médecin | soin | full record, read and write; confirms diagnostics |
  | infirmier | soin | full record, read and write; diagnostics provisional only |
  | caissier | caisse | ordonnances and amounts only |
  | pharmacien | pharmacie | paid lines, allergies, long-term treatments |
  | citoyen | citoyen | own carnet and own access log |

- **Access follows a relation de soin.** A soignant opens a dossier only when their établissement holds an open cas for that patient, or when they open or continue one now with the patient present. Caisse and pharmacie reach an ordonnance through the numéro the patient presents. Anything else is an accès d'urgence. See `docs/adr/0002-acces-par-relation-de-soin.md`.
- **Accès d'urgence** bypasses the relation de soin for vital emergencies, requires a stated reason, and is audited like any access.
- **Every read or write of a patient record emits an `AuditEvent`**: agent, facility, action, timestamp.
- **The citoyen signs in with NPI plus code carnet**, a short code printed on the receipt handed over at each visite. `identite` issues a `citoyen` token scoped to that NPI. No SMS in v1. See `docs/adr/0003-connexion-citoyen-par-code-carnet.md`.
- **Tokens are signed, short-lived, and verified independently by each service.** They travel in an `httpOnly`, `Secure`, `SameSite=Strict` cookie scoped to the application's subdomain; client JavaScript never reads them.
- **Synthetic data only.** Fixtures come from `donnees/`. Logs, commits, prompts, issues and test names carry resource ids, never names, NPIs or clinical content.
- **Secrets come from environment variables**; `.env` stays out of git.
- Population statistics run on de-identified extracts, never on the live record (analytics is out of v1 scope).

## Inclusivity requirement

The population served is not a connected one. Citizen screens are understandable without reading: the illustration carries the meaning, every action pairs an icon with a word, colour never carries meaning alone, WCAG 2.2 AA is the floor. UI work follows `prd_for_design.md` and the design system in `web/design/` and `docs/design/`.

## Scope

**v1 builds:** noyau and dataset (with tarifs); design system; `soin` (cas, visite, mesures including lab results entered by the soignant, diagnostic, ordonnance); `caisse` (encaissement without re-typing); `pharmacie` (traced délivrance, partial allowed); `citoyen` (illustrated carnet, code carnet sign-in); roles, relation de soin and audit; accès d'urgence. Each with its application.

**Designed, not built:** laboratoire service and application, télémédecine as a visite type, analytics warehouse, registries of professionals and établissements.

**Out of v1:** offline mode, voice, USSD and SMS, AI clinical scribe, AI diagnosis support, stock management, full insurance billing.

## Feature map

One PRD per session, in dependency order. Status lives in the issue tracker.

| # | Feature | Blocked by | Day |
|---|---|---|---|
| F0 | Design system: tokens, pictograms, components in `web/design/` | none | 1 |
| F1 | Socle: Compose, noyau, gateway and subdomains, `commun/`, web workspace, Azure deploy | none | 1 |
| F2 | Identité (agents, code carnet) and synthetic dataset with tarifs | F1 | 1 |
| F3 | Service and application soin, relation de soin | F0, F2 | 2 |
| F4 | Ordonnance to caisse: service and application | F3 | 2 |
| F5 | Pharmacie: service and application | F4 | 3 |
| F6 | Citoyen: service and carnet application | F3 | 3 |
| F7 | Accès d'urgence and access log | F3 | 3 |
