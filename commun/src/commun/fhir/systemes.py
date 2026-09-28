"""Les systèmes que Lafia emploie dans le noyau : ceux qu'il définit, et les standards qu'il reprend.

Un système nomme l'ensemble dont un code ou un identifiant fait partie. Ceux de Lafia vivent sous
`https://lafia.bj/fhir` : ce sont des noms, pas des adresses à joindre. Les services cherchent dans le
noyau par eux ; en changer demanderait de réécrire ce qu'il tient (ADR 0006).
"""

LAFIA = "https://lafia.bj/fhir"

# Identifiants
NPI = "https://npi.gouv.bj"
"""Le NPI, identifiant civil du patient : le seul identifiant de patient du noyau."""

TARIF = f"{LAFIA}/identifiant/tarif"
"""Un tarif, par son établissement et son produit : `cnhu-hkm:MED-PARACETAMOL-500`."""

# Systèmes de codes de Lafia
TYPE_DE_STRUCTURE = f"{LAFIA}/CodeSystem/type-de-structure"
"""Ce qu'est une Organization : un établissement, par son niveau dans la pyramide sanitaire, ou une officine."""

ROLE = f"{LAFIA}/CodeSystem/role"
"""Le rôle d'un agent, qualification de son Practitioner : les rôles des jetons (`commun.jeton.Role`)."""

CATALOGUE = f"{LAFIA}/CodeSystem/catalogue"
"""Les produits et actes qu'une ordonnance peut porter : `MED-PARACETAMOL-500`, `ACT-CONSULTATION`."""

# Systèmes de codes standard
ATC = "http://www.whocc.no/atc"
"""Classification ATC des médicaments, de l'OMS : `N02BE01`."""

CONTEXTE_D_USAGE = "http://terminology.hl7.org/CodeSystem/usage-context-type"
"""Dans quel contexte une définition s'applique : `venue`, le lieu."""

PAYS = "urn:iso:std:iso:3166"
"""Pays, par leur code ISO 3166 à deux lettres : `BJ`."""

LANGUE = "urn:ietf:bcp:47"
"""Langues, par leur code BCP 47 : `fr`, `fon`, `yo`, …"""

ROLE_DE_CONTACT = "http://terminology.hl7.org/CodeSystem/v2-0131"
"""Ce qu'est un contact pour le patient (HL7 v2, table 0131) : `C`, la personne à prévenir."""

# F3 : le dossier clinique. Les formes des ressources : docs/specs/F3-v1-complete.md, contrat FHIR.
ORDONNANCE = f"{LAFIA}/identifiant/ordonnance"
"""Le numéro d'ordonnance, `ORD-7K4-M2P` : `groupIdentifier` de chaque ligne, et identifiant de l'encaissement."""

RECEPISSE = f"{LAFIA}/identifiant/recepisse"
"""Le numéro du récépissé d'un encaissement : `REC-7K4-M2P`."""

LIGNE = f"{LAFIA}/identifiant/ligne"
"""Une ligne d'ordonnance payée, dans un encaissement : l'identifiant de son MedicationRequest."""

TYPE_DE_VISITE = f"{LAFIA}/CodeSystem/type-de-visite"
"""consultation, soins-infirmiers, continuite, urgence."""

DIAGNOSTIC = f"{LAFIA}/CodeSystem/diagnostic"
"""La courte liste des diagnostics que Lafia propose : `paludisme`, `ira`, `hta`, …"""

MOTIF_D_ACCES = f"{LAFIA}/CodeSystem/motif-d-acces"
"""Pourquoi un dossier est ouvert : `relation-de-soin`, `acces-urgence`, `citoyen`."""

LOINC = "http://loinc.org"
"""Les mesures, par leur code LOINC : `8310-5`, la température."""

UCUM = "http://unitsofmeasure.org"
"""Les unités des mesures : `Cel`, `mm[Hg]`, `kg`."""

CIM_10 = "http://hl7.org/fhir/sid/icd-10"
"""CIM-10 de l'OMS, en regard du diagnostic de Lafia : `B54`."""

DICOM = "http://dicom.nema.org/resources/ontology/DCM"
"""Le type d'un AuditEvent : `110110`, dossier patient."""

ACTION_REST = "http://hl7.org/fhir/restful-interaction"
"""Le sous-type d'un AuditEvent : `read`, `create`, `update`."""

MOMENT_DE_PRISE = "http://hl7.org/fhir/event-timing"
"""Les moments de prise d'une posologie : MORN, NOON, EVE, NIGHT."""

# F4 : le dossier approfondi (docs/specs/F4-dossier-approfondi.md).
TYPE_D_ANTECEDENT = f"{LAFIA}/CodeSystem/type-d-antecedent"
"""Ce qu'est un antécédent du patient : `medical` ou `chirurgical` (le familial est un FamilyMemberHistory)."""

CATEGORIE_DE_CONDITION = "http://terminology.hl7.org/CodeSystem/condition-category"
"""`problem-list-item` pour un antécédent, `encounter-diagnosis` pour le diagnostic d'une visite."""

VERIFICATION = "http://terminology.hl7.org/CodeSystem/condition-ver-status"
"""Un diagnostic `provisional` ou `confirmed`."""

LIEN_DE_PARENTE = "http://terminology.hl7.org/CodeSystem/v3-RoleCode"
"""Le lien d'un parent au patient : MTH, FTH, SIB, CHILD, GRMTH, GRFTH."""

# F5 : la Reprise du passé médical (docs/specs/F5-reprise-du-passe-medical.md, ADR 0007 et 0008).
ORIGINE = f"{LAFIA}/CodeSystem/origine"
"""D'où vient une entrée du dossier (`meta.tag`) : visite, numerisation, declaration, report ; `reprise` sur un Dépôt."""

TYPE_DE_DOCUMENT = f"{LAFIA}/CodeSystem/type-de-document"
"""carnet, compte-rendu, resultat-analyse, ordonnance, imagerie, certificat, autre."""

DEPOT = f"{LAFIA}/identifiant/depot"
"""Le Dépôt d'un Document (`meta.tag`), et de l'AuditEvent qui l'ouvre."""

LISIBILITE = f"{LAFIA}/StructureDefinition/lisibilite"
"""Extension d'un DocumentReference : lisible ou partiel."""

PAPIER_ABIME = f"{LAFIA}/StructureDefinition/papier-abime"
"""Extension d'un DocumentReference (valueString) : la note de l'agent quand un papier abîmé en lui-même
a passé outre un contrôle de la capture (F6.5)."""

# F6 : la Relecture et l'Extraction (docs/specs/F6-relecture-et-extraction.md, ADR 0009, 0010).
RELECTURE = f"{LAFIA}/CodeSystem/relecture"
"""L'étape d'une Tâche de relecture (`Task.code`) : `relecture`, `controle`, `validation` ; et l'activité
du Provenance d'une version de Transcription : `relecture` ou `controle`."""

ISSUE_DE_RELECTURE = f"{LAFIA}/CodeSystem/issue-de-relecture"
"""L'issue d'une Tâche (`Task.businessStatus`) : confirmee, relue, renvoyee, acceptee, non-medical, doublon."""

SEMAINE_DE_RELECTURE = f"{LAFIA}/identifiant/semaine-de-relecture"
"""La semaine d'une Tâche (`meta.tag`) : `2026-W39`."""

MODELE_DE_LECTURE = f"{LAFIA}/identifiant/modele-de-lecture"
"""Un modèle d'Extraction, en Device : `demonstration:0`."""

PIECE_D_IDENTITE = f"{LAFIA}/CodeSystem/piece-d-identite"
"""La pièce d'identité vérifiée au guichet, motif du Provenance d'un Dépôt : cni, passeport, acte-de-naissance, carte-lafia, autre."""
