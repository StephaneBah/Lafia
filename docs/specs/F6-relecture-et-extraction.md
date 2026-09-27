# F6 : Transcription du passé papier — capture rigoureuse, Relecture, Contrôle

Follows F5 (Reprise du passé médical). Grounded in ADR 0007 (the dossier only grows), 0008 (Documents in the noyau), 0009 (the Extraction contract) and 0010 (the Transcription format). The machine reading model does not exist yet: F6 builds everything around it with a stand-in, so the real model plugs in later without any other change. Revised on 2026-09-27 after the first draft made triage a gate that could only end by recalling the citizen.

## Problem Statement

The Reprise turns paper into Documents, but a Document is a set of photos: a soignant must decipher each page, doctors' handwriting is often illegible, and nothing can be regrouped by place or date. Reading millions of pages needs a machine, and trusting the result needs people with some medical literacy who correct it by hand. The citizen must not pay for any of this: they come to the desk once, and nothing after it may send them back.

## Principles

1. **The citizen comes once.** Everything that needs them (identity, legible pages, every page, in order) happens at the desk while they are there. They may come back on their own with papers they forgot; the platform never summons them. Their paper history is never closed: a later Dépôt adds Documents that join the same views.
2. **Quality is enforced at capture**, where fixing it costs ten seconds.
3. **The machine eases the work; people make it true.** The Extraction drafts a Transcription; agents de relecture correct and structure it, confirm it twice, and a second reviewer controls it.
4. **A Transcription is a heritage asset** of the patient's history before Lafia, not verified clinical data, and every screen says so.
5. **The citizen and the soignant benefit early**: the scan is in the dossier from the desk on; the Transcription joins it once relue.

## Solution

1. **Rigorous capture at the desk** (numerisation, and the soignant's "Ajouter un document"): every page is checked in the browser as it is taken: sharpness, brightness and contrast, framing (the page's edges inside the frame, minimum resolution), glare. A page that fails cannot be kept; a guide says what to change ("trop sombre : rapprochez-vous de la lumière", "page coupée : reculez"). The only override is a paper damaged in itself, declared by the agent and noted on the Document. Before closing a Document the agent confirms the page count against the paper and can reorder pages.
2. **Extraction** (stand-in today) reads each numérised Document and returns a draft Transcription in volets (ADR 0010), the raw text, and proposed clinical facts.
3. **Relecture** by an agent de relecture, from their weekly tâches: the pages scroll on the left, the rendered Transcription on the right, each volet pointing to its pages. They correct the reading by hand, reorder, split and merge volets, add photos of pages or regions, mark what is illegible. **Double confirmation**: first they tick each volet as checked against its pages, then they confirm the whole Transcription with a summary of their changes.
4. **Contrôle** by a second agent de relecture (never the same person): they read the confirmed Transcription against the pages and accept it, or send it back to the first with a note. Accepted, it becomes relue (`docStatus` final).
5. **Reading it**: soin's Documents tab shows the relue Transcription rendered next to the scan, labelled "Transcription d'un document ancien, relue — ce n'est pas une donnée clinique vérifiée". The carnet's "Mes documents" shows it too, and a **"Par établissement"** view regroups every volet of every relue Transcription by établissement, in date order.
6. **Clinical facts** (secondary): the Extraction's proposals wait in the Tâche; once the Transcription is relue, a soignant can validate them into the dossier (origine `extraction`, ADR 0009). The structured Transcription makes that work easier.
7. **Follow-up for reviewers**: "Ma semaine" (quota, done, returned by Contrôle), and the history of their Relectures and Contrôles.

## Decisions

- A Document's paper order is kept in its pages; the Transcription orders volets by date where known. Nothing is stored per établissement: that view is computed.
- Agents de relecture have some medical literacy; they transcribe and structure, never validate a clinical fact.
- Pseudonymised, not anonymous: the system never shows who the patient is; a page may. Tâches are assigned outside the reviewer's own département; every page view is audited; the citizen sees "Vos papiers ont été relus" without a name.
- Contrôle is systematic for now (every Transcription), with a configurable share (`PART_CONTROLEE`, default 1) so it can become sampling later.
- An unusable Document (not medical, duplicate) is marked so by the reviewer and closed; an illegible passage is a volet of type `illisible`. Nothing reopens the Dépôt or contacts the citizen.
- Designed, not built: the real model; automatic name blurring; a supervisor view; queue priorities; paying reviewers.

## FHIR contract (additions)

| Thing | Resource | Shape |
|---|---|---|
| Tâche de relecture | `Task` | `code` system `RELECTURE`: `relecture` \| `controle` \| `validation`; `status` ready \| in-progress \| completed \| rejected; `focus` = scanned DocumentReference; `for` = Patient (never shown); `owner` = reviewer; `restriction.period.end` = end of week; `output[]` = current Transcription; `contained[]` = proposals; `note[]` = Contrôle's return notes; `meta.tag` week |
| Transcription | `DocumentReference` | type Transcription; `text/markdown` Binary (ADR 0010); `relatesTo` transforms the scan, `replaces` the previous version; `docStatus` preliminary → final at Contrôle; `meta.tag` origine extraction |
| Relecture, Contrôle | `Provenance` | target the Transcription version; agent the reviewer; `activity` relecture \| controle; entity source the scan |
| Capture quality | DocumentReference extension `…/StructureDefinition/papier-abime` | valueString: the agent's note when a damaged paper overrode a check |

## Routes (relecture, under `/api/relecture`)

- `GET /taches` → my week: `[{id, etape: relecture|controle|validation, document:{type, annee, pages}, echeance, statut, renvoyee?}]`; assigns up to the quota.
- `GET /taches/{id}` → `{id, etape, document, transcription (Markdown), volets:[{titre, type, date, etablissement, pages}], texte, modele, notes_de_controle, propositions?}`; never the patient.
- `GET /taches/{id}/pages/{n}`.
- `PUT /taches/{id}/transcription {markdown}` → saves a working draft (in the Task, not yet a version).
- `POST /taches/{id}/confirmation {volets_verifies:[...], resume}` → writes a Transcription version, Provenance relecture, creates the Contrôle tâche for another reviewer.
- `POST /taches/{id}/controle {decision: accepter|renvoyer, note?}` → accept: final version + Provenance controle; send back: the relecture tâche returns to its reviewer with the note.
- `POST /taches/{id}/inutilisable {raison: non-medical|doublon}`.
- `POST /taches/{id}/validation` (soignant, clinical facts) as before.
- soin: `GET /api/soin/documents/{id}/transcription`; citoyen: `GET /api/citoyen/documents/{id}/transcription` and `GET /api/citoyen/par-etablissement`.

## Tickets

| # | Slice |
|---|---|
| F6.1 | Contract, glossary, ADR 0009/0010, `commun/fhir/relecture.py`, `commun/extraction.py` (done) |
| F6.2 | Extraction stand-in: draft Transcriptions in volets per ADR 0010 (done in a first form; extend) |
| F6.3 | relecture service: relecture, confirmation, contrôle, inutilisable, versions and Provenance; quota and follow-up |
| F6.4 | relecture application: side-by-side reviewer (pages left, rendered Transcription right, editing, volets, double confirmation), Contrôle screen, Ma semaine and history |
| F6.5 | Rigorous capture: shared quality checks in `web/commun`, used by the desk and soin; page count and reorder; damaged-paper override |
| F6.6 | Reading: shared Transcription parser/renderer (ADR 0010); soin Documents tab; carnet "Mes documents" and "Par établissement"; heritage label |

## Out of Scope

The real model and its server; name blurring; supervisor dashboards; paying reviewers; the citizen uploading papers themself.
