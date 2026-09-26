# F4 : dossier approfondi et parcours soignés

Follows F3 (v1 complète, `docs/specs/F3-v1-complete.md`). Built in parallel on the contract below.

## Problem Statement

F3 walks the whole journey, but testing it shows three gaps. The dossier has no medical history: no antécédents, no traitements au long cours, no groupe sanguin, so a soignant decides blind. The médecin's flow is confusing: "Continuer le cas" jumps into the visite form without showing the history, the fiche and the dossier are separate places, and nothing stays on screen to say whose dossier this is. The citizen's ordonnance screen is cramped: every past ordonnance is fully expanded, lines are tight. The code review adds privacy and structure debts: the NPI travels in soin URLs and access logs, audit motifs are wrong after a search or an accès d'urgence, a médecin can close another établissement's cas, FHIR reading sits in the soin service, helpers are copied across modules and apps.

## Solution

1. **Dossier approfondi.** A soignant with a relation de soin records antécédents (médicaux, chirurgicaux, familiaux), traitements au long cours and the groupe sanguin. The citoyen sees them read-only in the carnet; the pharmacien sees allergies and traitements au long cours.
2. **Espace patient in soin.** Searching an NPI leads in one step to the patient: a persistent **bandeau patient** (identity, age, groupe sanguin, allergies, antécédents, traitements au long cours) over three tabs: **Synthèse** (open cas, latest mesures, temperature chart, antécédents), **Cas** (timeline) and **Nouvelle visite** (stepped form: motif → mesures → diagnostic → ordonnance → reçu, with a live allergy warning on each product). Without a relation de soin, one clear choice: open a cas, continue one, or accès d'urgence. Continuing a cas shows its history before the form.
3. **Carnet aéré.** One card per ordonnance, one roomy row per médicament with a large pictogram, status badge (icon + word), moments as pictograms and "pendant N jours"; past ordonnances collapsed; same density rules on the cas screens; antécédents and traitements au long cours on a "Ma santé" screen; a line stopped for an allergy says so.
4. **Debts paid.** The NPI never appears in a URL or a log; audit motifs are right; closing a cas needs a relation with that cas; FHIR reading moves to `commun/fhir`; quantities carry their unit; "fiche", "facture", "ticket" leave code and UI.

## Decisions

- **Antécédent** is not a Diagnostic: no visite, no confirmation, outlives every cas (`CONTEXT.md`).
- Recorded by médecin or infirmier with a relation de soin, audited. Free text is allowed for an antécédent's label (history is told, not catalogued); a traitement au long cours uses the catalogue when the product is in it, free text otherwise.
- **Patients are addressed by their Patient id** in every soin route and page; the NPI is sent once, in a POST body, to `recherche`. Access logs are off in service containers.
- Audit motifs: `recherche` for the NPI search, `relation-de-soin`, `acces-urgence` (and every read by that soignant on that cas while it is open), `citoyen`, `numero-d-ordonnance`.
- Designed, not built: vaccinations, habitudes, grossesse.

## FHIR contract (additions to F3)

| Thing | Resource | Shape |
|---|---|---|
| Antécédent médical / chirurgical | `Condition` | `category[0].coding` = {`http://terminology.hl7.org/CodeSystem/condition-category`, `problem-list-item`}; `category[1].coding` = {system `TYPE_D_ANTECEDENT`, code `medical` \| `chirurgical`}; `code.text` = label; `clinicalStatus` active \| resolved; `onsetString` = year or free period; `subject`, `recorder`, `recordedDate`; **no `encounter`** |
| Diagnostic (F3, now explicit) | `Condition` | as F3, plus `category[0].coding` = {condition-category, `encounter-diagnosis`} |
| Antécédent familial | `FamilyMemberHistory` | `status` completed; `patient`; `relationship` = v3 RoleCode (`MTH` mère, `FTH` père, `SIB` frère/sœur, `CHILD` enfant, `GRMTH`/`GRFTH` grand-parent) with `text`; `condition[0].code.text`; `date` |
| Traitement au long cours | `MedicationStatement` | `status` active \| stopped; `subject`; `medicationCodeableConcept` (catalogue coding when known, always `text`); `dosage[0].text` + `timing.repeat.when`; `effectivePeriod.start`; `informationSource` = Practitioner; `dateAsserted` |
| Groupe sanguin | `Observation` | `code` LOINC `882-1`; `category` laboratory; `valueCodeableConcept.text` ∈ A+, A−, B+, B−, AB+, AB−, O+, O−; `subject`, `performer`, `effectiveDateTime`; latest wins |
| Quantities | `MedicationRequest` | `dispenseRequest.quantity` and `doseQuantity` carry `unit` (comprimé, gélule, flacon, sachet…) from the catalogue form |

New systems in `commun.fhir.systemes`: `TYPE_D_ANTECEDENT`, `CATEGORIE_DE_CONDITION`, `LIEN_DE_PARENTE` (v3 RoleCode), `VERIFICATION` (condition-ver-status).

## Soin HTTP API (replaces F3's `{npi}` routes)

- `POST /api/soin/recherche` `{npi}` → 200 `{patient_id}` \| 404. Audited, motif `recherche`.
- `GET /api/soin/patients/{patient_id}` → bandeau: `{patient:{id, npi, nom, prenoms, sexe, naissance, age}, groupe_sanguin, allergies:[{id, libelle, code_atc}], antecedents:[{id, type, libelle, depuis, actif}], familiaux:[{id, lien, libelle}], traitements:[{id, libelle, posologie, moments, depuis}], cas:[{id, motif, statut, etablissement, etablissement_id, de_mon_etablissement, debut}], relation_de_soin}`. Without relation de soin, `antecedents`, `familiaux`, `traitements` and cas motifs of other établissements are omitted (identity, allergies, groupe sanguin stay: they save lives).
- `GET /api/soin/patients/{patient_id}/dossier` → F3 dossier + `mesures_series:{<loinc>:[{date, valeur}]}` for charts. 403 without relation.
- `POST /api/soin/patients/{patient_id}/cas`, `/allergies`, `/acces-urgence`: as F3, by patient id. Allergies: `code_atc` must be in the allergy catalogue served by `GET /catalogue` (`allergies:[{code_atc, libelle}]`).
- `POST /api/soin/patients/{patient_id}/antecedents` `{type: "medical"|"chirurgical"|"familial", libelle, depuis?, lien? (familial: mere|pere|fratrie|enfant|grand-parent), actif?}` → 201 `{id}`.
- `POST /api/soin/patients/{patient_id}/traitements` `{produit?, libelle?, posologie, moments:[...]}` → 201 `{id}`; `POST /api/soin/traitements/{id}/arret` → 200.
- `PUT /api/soin/patients/{patient_id}/groupe-sanguin` `{valeur}` → 200.
- `POST /api/soin/cas/{cas_id}/visites`, `/cloture`: as F3; `cloture` needs a relation with **that** cas; `visites` on another établissement's cas is the "continuer" act and is allowed.
- `GET /api/soin/catalogue` adds `allergies` and each product's `forme` (unit).

## Citoyen HTTP API (additions)

- `GET /api/citoyen/sante` → `{groupe_sanguin, allergies, antecedents, familiaux, traitements}` in plain words. (Name clash with `/sante` health check: use `/api/citoyen/ma-sante`.)
- `/ordonnances` lines carry `unite` and `arret_allergie:bool` (a paid line never handed over while the patient has a matching allergy).

## Tickets

| # | Slice | Owner |
|---|---|---|
| F4.1 | Contract, glossary, access logs off, architecture doc | lead |
| F4.2 | Soin back end: antécédents, traitements, groupe sanguin, patient-id routes, audit motifs, per-cas closing, translation to `commun/fhir`, units; tests updated | agent soin-back |
| F4.3 | Soin front end: espace patient (bandeau, tabs, stepped visite, live allergy warning, temperature chart), history forms, no NPI in URLs | agent soin-front |
| F4.4 | Carnet aéré and "Ma santé", demo antécédents in `donnees/` | agent citoyen |
| F4.5 | Pharmacien sees traitements au long cours | lead, after F3.7 |
| F4.6 | Merge, suite, deploy | lead |

## Out of Scope

Vaccinations, habitudes, grossesse; shared app shell for caisse (later); editing or deleting an antécédent (append-only: a correction is a new entry, the old one marked resolved).
