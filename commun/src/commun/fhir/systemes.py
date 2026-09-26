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
