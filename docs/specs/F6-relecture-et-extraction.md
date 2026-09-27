# F6 : Relecture des Documents et Extraction — les fondations, démontrables

Follows F5 (Reprise du passé médical). Grounded in ADR 0007 (the dossier only grows), ADR 0008 (Documents in the noyau) and ADR 0009 (the Extraction contract). The machine reading model does not exist yet: F6 builds the workflow around it with a stand-in, so the real model plugs in later without any other change.

## Problem Statement

The Reprise turns paper into Documents, but a Document is an image: a soignant must open it and read it to use it, and nothing in it can be searched, charted or checked against a prescription. Reading millions of pages needs a machine, and trusting a machine needs people: someone to say a scan is usable before any machine reads it, and a soignant to accept each fact the machine proposes. None of this exists, and the team that will build the model needs a place to plug it in.

## Solution

1. **Tâches de relecture.** Each numérised Document gets a Tâche de relecture. Part-time agents de relecture receive a weekly quota of tâches, assigned outside their own département, and see only the pages: no NPI, no name from the system.
2. **Triage** by the agent de relecture: usable or not (illegible, not medical, wrong type, duplicate), the right type, a corrected year. A usable Document goes to Extraction.
3. **Extraction** through the `extraction` service (ADR 0009). Today it is a stand-in that answers the real contract with sample proposals, labelled "extraction de démonstration" everywhere.
4. **Clinical validation** by a soignant doing relecture: they see the pages beside the proposals, accept, correct or reject each one. Accepted proposals enter the dossier with origine `extraction`; the text becomes a derived Document.
5. **The patient** sees in "qui a ouvert mon dossier" that their Documents were read for relecture, without the reviewer's name.

## Decisions

- **Two tiers**: triage by agents de relecture (no clinical fact), validation by soignants (ADR 0007).
- **Pseudonymised, not anonymous**: the system never shows who the patient is; a page may. Assignment avoids the reviewer's own département; every view is audited.
- **Weekly quota**: set per reviewer (default 50 tâches); unfinished tâches return to the pool at the end of the week.
- **State in the noyau**: a Tâche de relecture is a FHIR `Task`; proposals are its `contained` resources until validated.
- **Carnet papier and annexes**: a carnet is one Document; its annexes are Documents attached to it (`context.related`), reviewed separately, opened together.
- **Designed, not built**: the real model, automatic name blurring on pages, priority rules for the queue (e.g. patients with an upcoming visite), reviewer quality statistics.

## FHIR contract (additions)

| Thing | Resource | Shape |
|---|---|---|
| Tâche de relecture | `Task` | `status` ready \| in-progress \| completed \| rejected; `intent` order; `code` = {system `RELECTURE`, code `triage` \| `validation`}; `focus` = DocumentReference; `for` = Patient (never shown to the reviewer); `owner` = Practitioner; `restriction.period.end` = due date (end of the week); `businessStatus.text` = triage verdict; `output[]` = the derived text Document and the validated entries; `contained[]` = Extraction proposals; `meta.tag` week `2026-W39` |
| Extraction text | `DocumentReference` | `relatesTo` = {code `transforms`, target the scan}; `content[0].attachment` text/plain as `Binary`; `category` origine `extraction`; `author` = the Device |
| Model | `Device` | `deviceName` = modele.nom; `version[0].value` = modele.version |
| Validated fact | Observation, Condition, AllergyIntolerance, MedicationStatement | as F4, `meta.tag` origine `extraction`, plus a `Provenance` (entity source the scan, agents the soignant and the Device) |
| Annexe | `DocumentReference` | `context.related[]` = the Carnet papier's DocumentReference |

## Services and routes

- `relecture` (new actor: roles `agent de relecture`, and médecin/infirmier for validation; its own application): `GET /api/relecture/taches` (my week), `GET /api/relecture/taches/{id}` (pages, no identity), `GET .../pages/{n}`, `POST .../triage {verdict, type?, annee?}`, `POST .../validation {propositions:[{id, decision: accepter|corriger|rejeter, valeur?}]}`.
- `extraction` (internal, no gateway route, no application): `POST /extraire` per ADR 0009; stand-in implementation.
- numerisation: Documents created from F6 on get a Tâche de relecture; annexes can be attached to a carnet at the desk.

## Tickets (after F5 is deployed)

| # | Slice |
|---|---|
| F6.1 | Contract: ADR 0009, glossary, systems, `commun/fhir/relecture.py` (Task, Device, Extraction helpers) |
| F6.2 | `extraction` stand-in service on the internal network, and its contract test |
| F6.3 | `relecture` service and actor: quota assignment, triage, extraction call, validation writing the dossier with Provenance |
| F6.4 | `relecture` application: my week, triage screen, validation screen (pages beside proposals) |
| F6.5 | Annexes at the desk; relecture shown in the carnet's access log; origine `extraction` shown in soin and the carnet |

## Out of Scope

The real model and its server; name blurring; queue priorities; statistics; paying reviewers.
