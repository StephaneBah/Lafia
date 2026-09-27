# 0007. The dossier only grows: contributions by role, origine on every entry

- Status: accepted
- Date: 2026-09-27

## Context

The dossier is fed by more and more actors: soignants at each visite (F3, F4), the caisse and the pharmacie, the Reprise of paper history (F5), later a laboratoire and other services. Each writes a different kind of fact, with a different level of trust: a diagnostic confirmed by a médecin, an antécédent told by the patient, a scanned page nobody has read yet. Invariant 8 already says records are append-only, but nothing yet says who may add what, or how a reader tells a verified fact from a declared one.

## Decision

- **Contributions by role.** Each role adds only its own kind of entry, through its own service, and reads only what its role needs. Nobody updates another actor's entry and nobody deletes: a correction is a new entry that supersedes the old one, and the old one stays readable in the noyau's history.

  | Role | Adds | Reads |
  |---|---|---|
  | médecin, infirmier | cas, visites, mesures, diagnostics, ordonnances, antécédents, allergies, traitements au long cours, groupe sanguin; reports from a Document | the full dossier, with a relation de soin |
  | agent de numérisation | Documents, grouped in a Dépôt | the patient's name and birth year to check identity, and the Documents of the current Dépôt |
  | agent de relecture | the triage verdict of a Tâche de relecture | the pages of the Documents assigned to them, pseudonymised |
  | médecin, infirmier (relecture) | entries validated from an Extraction (origine `extraction`) | the assigned Document and its Extraction |
  | caissier | encaissements | ordonnances by numéro |
  | pharmacien, officine | délivrances | as in `SYSTEM_PROMPT.md` |
  | citoyen | nothing | their own carnet, Documents included |
  | laboratoire (designed) | results and their Documents | the demands addressed to it |

- **Origine on every entry.** Every resource a service writes carries a `meta.tag` in the system `https://lafia.bj/fhir/CodeSystem/origine`: `visite`, `numerisation`, `declaration` (told by the patient), `report` (keyed in by a soignant from a Document), `extraction` (proposed by a machine, validated by a soignant; ADR 0009). Every screen shows it, so a reader always knows how much to trust an entry.
- **Provenance links an entry to what it came from.** A Dépôt is a FHIR `Provenance` whose targets are its Documents, with the agent de numérisation, their établissement and the identity check used. A report from a Document is a `Provenance` whose target is the new entry and whose source entity is the `DocumentReference`.
- **Supersession, not edition.** A superseding entry points to the one it replaces (`DocumentReference.relatesTo` `replaces`; for other resources a `Provenance` with the old one as a `revision` source), and the old one moves to its standard "entered in error" or "superseded" status in a new version.

## Consequences

- Any new actor joins by declaring its row in this table, its own service and its origine code; nothing else changes.
- Readers can filter by origine (`_tag`) and show "numérisé, non vérifié" next to a scan and "déclaré par le patient" next to an antécédent.
- A wrong entry stays visible in history; that is the price of an auditable record.
- Rejected: a single "editor" role that can fix anything (one account becomes the most dangerous in the country); a trust score per entry (false precision); editing in place with an audit log beside it (the audit log becomes the real record, and two records drift).
