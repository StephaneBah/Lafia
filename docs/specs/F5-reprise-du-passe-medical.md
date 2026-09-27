# F5 : Reprise du passé médical — numérisation, Documents, origine des entrées

Follows F4. Issue #30 ("F'0") is its origin. Grounded in ADR 0007 (the dossier only grows) and ADR 0008 (Documents in the noyau).

## Problem Statement

A citizen's medical past is on paper: old carnets, comptes rendus, lab reports, prescriptions, kept at home or lost. Lafia starts every dossier empty, so the soignant still decides without the past, and the paper keeps getting lost. At the same time the dossier is now fed by several actors with different levels of trust, and nothing yet tells a reader whether an entry was verified at a visite, told by the patient, or copied from a scan.

## Solution

1. **Numérisation at a desk.** An agent de numérisation, a new actor with its own application and service (`numerisation`), receives a citizen with their papers. They enter the NPI, check an ID document and declare it, see the person's name and birth year to confirm, then numérise each paper as a Document: type, year, établissement d'origine, legibility, one or more pages by camera or file. Closing the Dépôt records it. The papers go back to the citizen.
2. **During a visite.** A soignant can add a Document the patient brought, from the patient workspace, with the same form.
3. **Documents in the dossier.** Soin shows a "Documents" tab with each Document marked "numérisé, non vérifié", with a page viewer. The carnet has "Mes documents". A soignant can report an antécédent or an allergy from a Document: the new entry carries origine `report` and a link to its Document.
4. **Origine everywhere.** Every entry written from now on carries its origine (ADR 0007), and soin and the carnet show it.

## Decisions

- **The Reprise** is the nationwide programme; in v1 it is a label on each Dépôt (`reprise: true` and the desk's établissement), enough to count. Planning desks and quotas is designed, not built.
- **The agent de numérisation adds Documents only.** They never key in clinical values: a wrong allergy typed at a desk is dangerous. Reports from a Document are a soignant's act, with a relation de soin.
- **Identity at the desk**: NPI plus an ID document checked by the agent (`cni`, `passeport`, `acte-de-naissance`, `carte-lafia`…), declared, audited, recorded on the Dépôt. The service returns the patient's name and birth year so the agent can compare them with the paper. Checking the code carnet at the desk is designed, not built: identite would need a verification route for agents, which is a guessing oracle to design carefully.
- **Structuring beyond reports** (OCR, automatic extraction) is designed, not built, and when built, always validated by a soignant.
- **Capture**: camera page by page with preview and retake, or file upload (JPEG, PNG, PDF); compressed in the browser per ADR 0008.
- **The citoyen** sees their Documents and each Dépôt in "qui a ouvert mon dossier", so a paper added to the wrong NPI is noticed.

## FHIR contract

| Thing | Resource | Shape |
|---|---|---|
| Page | `Binary` | `contentType` image/jpeg \| image/png \| application/pdf; `data`; `securityContext` = Patient |
| Document | `DocumentReference` | `status` current; `docStatus` final; `type.coding` system `TYPE_DE_DOCUMENT`: carnet, compte-rendu, resultat-analyse, ordonnance, imagerie, certificat, autre (with display); `category` = {system `ORIGINE`, code `numerisation`}; `subject`; `date` = capture instant; `author` = Practitioner who numérised; `context.period.start` = year of the original (`"2019"`); `context.sourcePatientInfo` = Patient; `description` = établissement d'origine as written; `content[]` = one attachment per page {`contentType`, `url` `Binary/<id>`, `size`, `title` "Page n"}; extension `https://lafia.bj/fhir/StructureDefinition/lisibilite` valueCode lisible \| partiel; `meta.tag` origine numerisation |
| Dépôt | `Provenance`, written at closing | `target[]` = its DocumentReferences (FHIR R4 needs at least one, so an empty dépôt writes nothing); `recorded`; `activity` = {system `ORIGINE`, code `numerisation`}; `agent[0]` = {`who` Practitioner, `onBehalfOf` Organization of the desk}; `reason[0]` = identity check, `coding` {system `https://lafia.bj/fhir/CodeSystem/piece-d-identite`, code `cni`…, display} and `text` its label; `meta.tag` = {system `DEPOT`, code `<depot_id>`}, {system `ORIGINE`, code `numerisation`}, and {system `ORIGINE`, code `reprise`} when part of the Reprise. Each DocumentReference of the dépôt also carries the `DEPOT` tag, so the dépôt is found by `_tag` before it closes |
| Report from a Document | `Provenance` | `target[0]` = the new Condition / AllergyIntolerance; `entity[0]` = {`role` source, `what` DocumentReference}; `agent[0]` = soignant |
| Origine | `meta.tag` | system `ORIGINE` (`https://lafia.bj/fhir/CodeSystem/origine`): visite, numerisation, declaration, report; on every resource services write from F5 on |

## HTTP API

numerisation (role `agent de numérisation`):
- `POST /api/numerisation/depots` `{npi, piece: "cni"|"passeport"|"acte-de-naissance"|"carte-lafia"|"autre", reprise: bool}` → 201 `{depot_id, patient:{nom, prenoms, annee_de_naissance}}` \| 404. `depot_id` is a fresh random id signed into nothing: the opening `AuditEvent` (motif `numerisation`, entity the Patient) carries the `DEPOT` tag, so the service finds the dépôt's patient and the agent who opened it by `AuditEvent?_tag=`, and its Documents by `DocumentReference?_tag=`. Only that agent may add to or read the dépôt, and only until it is closed.
- `POST /api/numerisation/depots/{depot_id}/documents` multipart: `type`, `annee`, `etablissement?`, `lisibilite`, `pages[]` (files) → 201 `{document_id, pages}`; 413 over the limits; 422 on a bad type/format.
- `GET /api/numerisation/depots/{depot_id}` → `{patient:{nom, prenoms, annee_de_naissance}, documents:[Document]}` (only this dépôt's Documents), each in the one Document view soin and citoyen also return: `{id, type, libelle, annee, etablissement, lisibilite, pages, formats, origine, depose_le}`.
- `GET /api/numerisation/depots/{depot_id}/documents/{id}/pages/{n}` → the page bytes (only this dépôt, for the preview).
- `POST /api/numerisation/depots/{depot_id}/cloture` → 200; after closing, nothing more can be added or read through the dépôt.

soin (médecin, infirmier, with relation de soin):
- `GET /api/soin/patients/{patient_id}/documents` → `[{id, type, annee, etablissement, lisibilite, pages, origine, depose_le}]`.
- `GET /api/soin/documents/{id}/pages/{n}` → bytes, audited.
- `POST /api/soin/patients/{patient_id}/documents` multipart (as numerisation) → 201: a Document added during a visite, origine `numerisation`, author the soignant.
- `POST /api/soin/patients/{patient_id}/antecedents` and `/allergies` accept `document_id?`: the entry gets origine `report` and a report `Provenance`.

citoyen: `GET /api/citoyen/documents` and `GET /api/citoyen/documents/{id}/pages/{n}`; `/acces` shows dépôts.

## Tickets

| # | Slice |
|---|---|
| F5.1 | Contract, glossary, ADR 0007/0008, systems, `commun/fhir/documents.py` (Binary, DocumentReference, Provenance, origine tag helpers) |
| F5.2 | Actor numerisation: role, identite application and demo accounts, compose service and application, gateway route, service routes, `docs/architecture.md`; tests |
| F5.3 | Application numerisation: desk flow (NPI + pièce, confirm identity, capture by camera or file with compression, Document form, dépôt summary, close) |
| F5.4 | Documents in soin (tab, viewer, add during visite, report from a Document) and in the carnet (Mes documents, dépôts in the access log); origine shown |

## Out of Scope

OCR and automatic structuring; the citizen uploading their own papers; code carnet at the desk; Reprise planning (desks, quotas, statistics); MinIO; editing or deleting a Document (a wrong one is superseded).
