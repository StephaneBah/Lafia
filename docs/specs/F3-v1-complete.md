# F3 : v1 complète — soin, caisse, pharmacie, carnet, accès d'urgence

Replaces the old F3 to F7 of the feature map: one PRD, sliced by actor along the demo path, built in parallel on a shared FHIR contract.

## Problem Statement

The socle, identite, the dataset and the design system are live, but no actor can do their work yet: a soignant cannot open a dossier, the caisse cannot take a payment, the pharmacie cannot hand anything over, and the citoyen's carnet is a status page. The jury must be able to walk the full journey on the deployed platform.

## Solution

The demo path, end to end, on the screens of `docs/design/maquettes/ecrans-lafia.html`:

1. **Soin.** A soignant searches a patient by NPI, sees identity, allergies and the list of cas, opens a new cas or continues one (which establishes the relation de soin), records a visite with mesures, a diagnostic and an ordonnance, then prints the reçu: numéro d'ordonnance, QR code, code carnet. A médecin can close a cas. Without relation de soin, an accès d'urgence with a stated reason opens the dossier.
2. **Caisse.** The caissier types or scans the numéro d'ordonnance, sees the lignes priced from the tarifs of their établissement, ticks the lignes to pay, and prints the récépissé. Nothing is typed but the numéro.
3. **Pharmacie.** The pharmacien types the numéro, sees the paid lignes not yet handed over, is stopped by an allergy that matches a ligne until they acknowledge it, and records a délivrance, partial allowed.
4. **Citoyen.** With NPI and code carnet the citoyen opens an illustrated carnet: home, current ordonnance and its payment and hand-over status, "Mon traitement" by moment of the day, each cas and its visites, and who opened the dossier.

Every read or write of a dossier emits an `AuditEvent`.

## Decisions

- **Relation de soin (ADR 0002)** is declared: opening a cas, or continuing one, with the patient present is the soignant's act, and it is audited. It holds while the patient has an active cas that has a visite at the soignant's établissement, or whose `managingOrganization` is that établissement. The NPI search alone shows identity, allergies and cas titles, nothing clinical.
- **Catalogues, never free text for what is priced or charted:** mesures from a fixed LOINC list, ordonnance lignes only from products with a tarif at the établissement, posology structured as moments (matin, midi, soir, nuit) × number of days, and diagnostics from a short coded list plus a note.
- **Closing a cas** is a médecin's act. An infirmier's diagnostic is provisional only.
- **The pharmacie** hands over lignes paid at the caisse of the same établissement; allergy matching is by ATC class prefix.
- **Cut from v1, designed not built:** the officine's check of an ordonnance and its declaration of lignes sold (F3.7, stretch), and paiement différé.
- **Tests:** one black-box test per slice through the gateway, one main path and one refusal.

## FHIR contract

Every service reads what another writes, so the shapes below are the contract. Systems live in `commun.fhir.systemes`; the shared helpers (client search, create, audit, numéro d'ordonnance) in `commun.fhir`. A service puts its own translation in `commun/fhir/<domaine>.py`.

| Thing | Resource | Shape |
|---|---|---|
| Cas de visite | `EpisodeOfCare` | `status` active \| finished; `patient`; `managingOrganization` = établissement where opened; `careManager` = Practitioner; `period.start/end`; `type[0].text` = motif |
| Visite | `Encounter` | `status` finished; `class` AMB (EMER for accès d'urgence); `type[0].coding` system `TYPE_DE_VISITE`: consultation, soins-infirmiers, continuite, urgence; `subject`; `episodeOfCare[0]`; `participant[0].individual` = Practitioner; `serviceProvider` = établissement; `period.start`; `reasonCode[0].text` = motif |
| Mesure | `Observation` | `status` final; `category` vital-signs \| laboratory; `code.coding` LOINC; `subject`, `encounter`, `effectiveDateTime`, `performer`; `valueQuantity` (UCUM), or `component` systolic/diastolic for tension, or `valueCodeableConcept` positif/négatif for a TDR |
| Diagnostic | `Condition` | `clinicalStatus` active \| resolved; `verificationStatus` provisional \| confirmed; `code.coding` system `DIAGNOSTIC` + ICD-10; `note[0].text`; `subject`, `encounter`, `recorder` |
| Allergie | `AllergyIntolerance` | `patient`; `code.coding` ATC class (e.g. `M01A` for AINS) + `code.text`; `recorder` |
| Ligne d'ordonnance | `MedicationRequest` | `status` active; `intent` order; `groupIdentifier` = {system `ORDONNANCE`, value `ORD-7K4-M2P`}; `medicationCodeableConcept.coding` catalogue code (+ ATC); `subject`, `encounter`, `requester`, `authoredOn`; `dispenseRequest.performer` = établissement; `dispenseRequest.quantity`; `dosageInstruction[0]`: `timing.repeat.when` ⊂ MORN, NOON, EVE, NIGHT, `timing.repeat.boundsDuration` {days}, `doseAndRate[0].doseQuantity`, `text` |
| Encaissement | `Invoice` | `status` balanced; `identifier` = {system `RECEPISSE`, value `REC-…`} and {system `ORDONNANCE`, value numéro}; `subject`; `issuer` = établissement; `participant[0].actor` = caissier; `date`; `lineItem[].chargeItemCodeableConcept.coding` = {system `LIGNE`, code MedicationRequest id}, `priceComponent` base amount; `totalGross` XOF |
| Délivrance | `MedicationDispense` | `status` completed; `authorizingPrescription` = MedicationRequest; `medicationCodeableConcept`; `subject`; `quantity`; `performer` Practitioner and établissement; `whenHandedOver` |
| Accès | `AuditEvent` | `type` DICOM 110110; `subtype` read \| create \| update; `action` R \| C \| U; `recorded`; `outcome` 0; `agent[0].who` = Practitioner or Patient, `requestor` true, `purposeOfUse` relation-de-soin \| acces-urgence \| citoyen, reason in `purposeOfUse[0].text`; `source.observer` = établissement, `source.site` = service; `entity[0].what` = Patient |

A ligne is paid when an `Invoice` carries its id; it is handed over by the sum of its `MedicationDispense.quantity`. Acts and examens (`ACT-`, `EXA-`) are paid, never handed over.

## Tickets

| # | Slice | Owner |
|---|---|---|
| F3.1 | Shared FHIR contract: systems, client search/create/read, audit, numéro d'ordonnance | lead |
| F3.2 | Soin: NPI search, relation de soin, cas, visite, mesures, diagnostic, ordonnance, reçu, closing a cas | agent soin |
| F3.3 | Accès d'urgence: reason, EMER visite, audit | agent soin |
| F3.4 | Caisse: ordonnance by numéro, tarifs, encaissement, récépissé | agent caisse |
| F3.5 | Pharmacie: paid lignes, allergy stop, délivrance partielle | agent pharmacie |
| F3.6 | Citoyen: carnet screens, access log, demo clinical history in `donnees/` | agent citoyen |
| F3.7 | Officine: check an ordonnance, declare lignes sold (stretch) | agent pharmacie |
| F3.8 | Merge, full suite, deploy, update `architecture.md` and the HTML deliverables | lead |

## Out of Scope

Paiement différé, stock, the officine API, laboratoire, télémédecine, analytics, account administration, SMS.
