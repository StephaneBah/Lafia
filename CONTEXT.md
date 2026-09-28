# Lafia

Shared digital health record for Benin: a FHIR core holding each citizen's medical data, reached by NPI, with domain services for care, cashier, pharmacy and citizen access.

## Language

**NPI**:
Numéro Personnel d'Identification, the citizen's civil identifier. The only key a citizen needs to be cared for.
_Avoid_: patient id, matricule

**Patient**:
A citizen as known to the care system, identified by their NPI.
_Avoid_: usager, malade

**Citoyen**:
The same person acting on their own behalf through the citizen interface.

**Dossier**:
Everything the core holds about one patient, as seen by authorised agents.
_Avoid_: fiche, DPI

**Carnet**:
The citizen-facing, simplified view of their own dossier.

**Cas de visite**:
One health problem from opening to closure. Groups every visite, mesure, diagnostic, ordonnance and délivrance tied to it; may span several établissements and several days.
_Avoid_: épisode, affaire, dossier (for this meaning)

**Visite**:
One real contact between a patient and the care system, always inside exactly one cas de visite. A consultation is one type of visite; so are a nursing encounter, a continuity visit and an emergency admission.
_Avoid_: consultation (as the generic term), rendez-vous

**Visite de continuité**:
A later visite attached to an already open cas de visite.

**Mesure**:
Any dated numeric value: a vital sign taken at the bedside or a lab result.
_Avoid_: constante (covers only part of the meaning)

**Diagnostic**:
What a soignant retains about the cas, provisional or confirmed.

**Antécédent**:
A lasting fact about the patient's health, true beyond any single cas: a past or chronic illness, a surgery, an illness in the family. Told by the patient or known from the dossier; never "confirmed" like a diagnostic.
_Avoid_: historique, passé médical

**Traitement au long cours**:
A medicine the patient takes continuously, whoever prescribed it, recorded so that every soignant and the pharmacien see it.
_Avoid_: traitement chronique, traitement de fond

**Groupe sanguin**:
The patient's ABO and Rhesus group, recorded once.

**Document**:
A file in the dossier that is not structured data: a scanned page of an old carnet, a compte rendu, a lab report, an image. Typed and dated; its origin says whether it was produced in Lafia or numérisé from paper.
_Avoid_: pièce jointe, archive, scan (for the thing itself)

**Numérisation**:
Turning a paper document the patient holds into a Document of their dossier. The paper goes back to the patient; Lafia keeps the Document.
_Avoid_: archivage, digitalisation

**Dépôt**:
One person's batch of paper documents handed over at a desk and numérisés in one sitting.
_Avoid_: lot, envoi

**Reprise**:
The nationwide, medium-term programme that numérises the paper medical past citizens hold, at desks in établissements and wherever else it is organised. A backfill: once a person's past is in, their dossier grows from the actors' own additions.
_Avoid_: campagne, recensement, migration

**Origine**:
Where an entry of the dossier comes from: a visite, a numérisation, the patient's own declaration, a report from a Document by a soignant, or an Extraction validated by a soignant. Every entry carries it, and every screen shows it.
_Avoid_: source (too vague), fiabilité

**Agent de numérisation**:
An agent who performs numérisations, for the Reprise or at any desk. Adds Documents to a dossier; reads nothing else in it.

**Carnet papier**:
The paper health booklet a patient holds, as opposed to their Carnet in Lafia. Numérisé whole as one Document of type carnet de santé, its pages in order.
_Avoid_: carnet (alone, for the paper one)

**Annexe**:
A loose paper found with a Carnet papier (a lab result, a compte rendu) and numérisé as its own Document, attached to the carnet's Document so they open together.
_Avoid_: pièce jointe, recueil

**Relecture**:
The work that turns a numérised Document into a trustworthy Transcription: the reviewer compares the machine's reading with the pages (scan on one side, rendered text on the other), corrects it by hand, puts the volets in order, then confirms twice; a second reviewer's Contrôle follows. Never recalls the citizen. Pseudonymised: the reviewer never sees who the patient is from the system, though a page may show a name.
_Avoid_: correction, triage

**Agent de relecture**:
A part-time agent with some medical literacy (doctors' handwriting is often illegible) who performs Relectures and Contrôles from a weekly quota of tâches. Transcribes and structures; validates no clinical fact.
_Avoid_: correcteur, opérateur de saisie

**Tâche de relecture**:
One Document to relire, assigned to one reviewer with a due date; then, once confirmed, a Contrôle by another reviewer.

**Transcription**:
The structured, human-reviewed reading of a numérised Document: its content in volets, with photos of the pages where they help, in date order where the dates are known. A heritage asset of the patient's history from before Lafia, not verified clinical data, and always labelled so. Each correction is a new version.
_Avoid_: OCR, résumé, compte rendu (for this meaning)

**Volet**:
One section of a Transcription: one visite, one lab result, one ordonnance, one vaccination page, with its date and établissement when the paper gives them, and the pages it comes from.
_Avoid_: rubrique, chapitre

**Contrôle**:
The second reviewer's check of a confirmed Transcription before it is marked relue: they read it against the pages and accept it or send it back with a note.
_Avoid_: validation (reserved for a soignant accepting clinical facts)

**Extraction**:
What a machine reads from a Document: a draft Transcription and the facts it proposes (a mesure, an antécédent, an allergy, a traitement). Its purpose is to ease the reviewers' work, never to be trusted alone: the draft becomes a Transcription only through Relecture, and a fact enters the dossier (origine extraction) only when a soignant validates it.
_Avoid_: OCR (the technique, not the result), IA (in UI)

**Ordonnance**:
A prescription issued at the end of a visite, identified by a unique numéro d'ordonnance, made of lignes.
_Avoid_: prescription (for the whole document)

**Numéro d'ordonnance**:
The short code that identifies an ordonnance at the caisse and the pharmacie, e.g. `ORD-7K4-M2P`. Readable aloud, typeable without a scanner.
_Avoid_: référence, ticket

**Ligne d'ordonnance**:
One product or act on an ordonnance. The unit that is paid, then dispensed, possibly separately and partially.

**Tarif**:
The price in FCFA of a product or act, looked up by the caisse so that no amount is typed.
_Avoid_: prix saisi

**Encaissement**:
Payment of some or all lignes of an ordonnance at the caisse.
_Avoid_: facture, vente

**Récépissé**:
The proof of encaissement handed over at the caisse; the pharmacie hands over the paid lignes against it, when they are in stock.
_Avoid_: reçu (for this meaning), facture

**Paiement différé**:
Care started before payment, for vital emergencies; settled afterwards.

**Délivrance**:
What a pharmacie or an officine actually hands over for a ligne. May be partial; a partial délivrance is a normal state.
_Avoid_: dispensation, vente

**Soignant**:
A médecin or infirmier writing in the dossier.

**Agent**:
Any authenticated professional user: soignant, caissier, pharmacien, agent de numérisation or agent de relecture.

**Établissement**:
A health facility where visites happen.

**Pharmacie**:
The pharmacy of an établissement, where paid lignes are handed over against the récépissé.

**Officine**:
An independent pharmacie de ville, attached to no établissement, which sells through its own management and payment software.
_Avoid_: pharmacie (for this meaning)

**Structure**:
An établissement or an officine: a place that holds agents or signs in under its own name. Each is an `Organization` in the noyau, typed by its level or as an officine.
_Avoid_: organisation, lieu

**Relation de soin**:
What entitles a soignant to open a dossier: their établissement holds an open cas de visite for the patient, or they open or continue one now with the patient present.
_Avoid_: consentement (the patient does not sign anything in v1)

**Accès d'urgence**:
A dossier access without relation de soin in a vital emergency; requires a stated reason, and is audited.
_Avoid_: break-the-glass (in code and UI)

**Reçu**:
The paper handed to the patient at the end of each visite: the numéro d'ordonnance when there is one, and the code carnet.
_Avoid_: ticket, bon

**Code carnet**:
The short code printed on the reçu. With the NPI, it lets the citoyen open their carnet.
_Avoid_: mot de passe, PIN

**Noyau**:
The FHIR server holding all medical data.
_Avoid_: backend, database

**Service**:
A domain software component around the noyau: identite, soin, caisse, pharmacie, citoyen.

**Application**:
The interface of one actor, paired with its service: application citoyen, soin, caisse, pharmacie.
_Avoid_: front, portail

## Relationships

- A **Patient** has one **Dossier** and many **Cas de visite**
- A **Dossier** only grows: each actor adds within its own reach, nobody edits or deletes; a correction is a new entry that supersedes the old one
- A **Document** has at most one current **Transcription**, made of **Volets**; the dossier's paper history is never closed: a later **Dépôt** adds Documents that join the same views
- The carnet's view by établissement is computed from the **Volets** of every relue **Transcription**, in date order; nothing is stored per établissement
- A **Dépôt** produces one or more **Documents**, each numérisé from paper and attached to the patient's **Dossier**
- A **Dossier** holds **Antécédents**, **Allergies**, **Traitements au long cours** and a **Groupe sanguin**, which outlive any **Cas de visite**; a **Diagnostic** belongs to one **Cas de visite**
- A **Cas de visite** holds one or more **Visites** and may span several **Établissements**
- A **Visite** produces **Mesures**, **Diagnostics** and at most one **Ordonnance** per issue
- An **Ordonnance** has many **Lignes d'ordonnance**
- A **Ligne d'ordonnance** is either paid by an **Encaissement** then handed over by the **Pharmacie**, or sold by an **Officine**, whose payment stays in its own software; each hand-over is a **Délivrance**, and there may be several
- A **Ligne d'ordonnance** is priced by a **Tarif**
- A **Service** reads and writes the **Noyau** only, never another **Service**
- An **Application** calls its own **Service** and `identite`, never the **Noyau**
- A **Soignant** opens a **Dossier** through a **Relation de soin** or an **Accès d'urgence**
- An **Officine** checks an **Ordonnance** by its numéro or QR code (prescriber, date, établissement) before selling its **Lignes**
- An **Officine** signs in under its own name; its pharmaciens have no account in Lafia
- A **Patient** has at most one valid **Code carnet**: the one on their latest **Reçu**; each new one replaces the previous

## Flagged ambiguities

- "service" means a hospital department in everyday Beninese usage. Resolved: **Service** is the software component only; a hospital department is an **Unité**.
- "consultation" was used for every contact. Resolved: the generic term is **Visite**; consultation is one type.
- "dossier" was used for both the whole record and one health problem. Resolved: **Dossier** is the whole record; one problem is a **Cas de visite**.
- "pharmacie" was used for both a hospital's pharmacy and an independent one. Resolved: the **Pharmacie** belongs to an **Établissement** and hands over lignes paid at its caisse; an independent one is an **Officine**, with its own payment.
- The agent de santé communautaire was listed as a **Soignant**, but has no role and works outside any **Établissement**. Resolved: a **Soignant** is a médecin or an infirmier; the agent de santé communautaire is out of v1.