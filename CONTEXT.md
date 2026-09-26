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
Any authenticated professional user: soignant, caissier or pharmacien.

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