# 0009. Extraction is a stateless, versioned service; only a soignant turns its proposals into the dossier

- Status: accepted
- Date: 2026-09-27

## Context

The Reprise fills dossiers with scanned Documents (F5, ADR 0008). Their value is locked in images until someone reads them. A machine reading model (OCR plus clinical extraction) will run later on a government server; it does not exist yet, and the team that builds it needs a contract today. Three risks shape it: a model that remembers what it read is a second, uncontrolled medical record; a model's mistakes must be traceable to the model version that made them; and a machine must never write a clinical fact into a dossier on its own (ADR 0007: only a soignant adds clinical facts).

## Decision

- **Stateless service.** `extraction` receives one Document's pages and returns an Extraction; it stores nothing but technical logs, which carry ids and timings, never page content or results. It is reached only by the `relecture` service, over the internal network, never by an application or the noyau.
- **Contract.** `POST /extraire` with `{document_id, pages:[{format, octets base64}], type_de_document}` returns `{modele:{nom, version}, texte, propositions:[<FHIR resource draft>], confiance_par_proposition}`. Drafts are FHIR R4 resources of the kinds the dossier already holds (Observation, Condition with category problem-list-item, AllergyIntolerance, MedicationStatement), without id, subject or recorder: the caller fills those. A new model version changes `version`, never the shape.
- **Proposals live in the Task, not the dossier.** The `relecture` service stores an Extraction as the output of the Tâche de relecture (a FHIR `Task` in the noyau): the text as a derived Document (`DocumentReference.relatesTo` `transforms` the scan), the drafts as `contained` resources of the Task. Nothing enters the dossier until a soignant validates it.
- **Validation writes the dossier.** Each validated proposal becomes a normal entry with origine `extraction` and a `Provenance`: entity the source Document, agents the validating soignant and the model as a FHIR `Device` (name and version). A rejected proposal stays in the Task only, to measure the model.
- **Until a model exists**, a stand-in `extraction` answers the same contract with fixed sample proposals and `modele: {nom: "demonstration", version: "0"}`, and every screen labels its results "extraction de démonstration".

## Consequences

- The model team builds against a fixed HTTP contract and can replace the stand-in without any other change.
- Every fact that came from a machine names the model version and the soignant who accepted it; a faulty version can be found and its facts reviewed.
- Reading a Document twice costs a second extraction; accepted, since nothing is cached outside the noyau.
- Rejected: the model writing proposals straight into the dossier as "unconfirmed" entries (the dossier fills with machine guesses nobody reviewed); the model keeping its own store of results (a second medical record outside the noyau and its audit).
