"""Traduction des choses que Lafia nomme (`commun.modele`) en ressources FHIR du noyau.

Chaque ressource garde l'identifiant fixe de la chose qu'elle traduit : l'écrire deux fois la met à
jour, sans doublon. Systèmes de codes et d'identifiants : `commun.fhir.systemes` (ADR 0006).
"""

import re
from typing import Any

from commun.fhir import systemes
from commun.fhir.client import Ressource
from commun.modele import Agent, Etablissement, Niveau, Officine, Patient, Sexe, Tarif

PAYS_DU_NOYAU = "BJ"
DEVISE = "XOF"
"""Le franc CFA d'Afrique de l'Ouest, code ISO 4217 du FCFA."""

# Ce qu'un identifiant de ressource FHIR admet.
IDENTIFIANT_FHIR = re.compile(r"[A-Za-z0-9\-.]{1,64}")

# Patient : les extensions standard (HL7) de son lieu de naissance et de sa nationalité, son genre,
# et le code de la personne à prévenir parmi ses contacts (`systemes.ROLE_DE_CONTACT`).
EXTENSION_LIEU_DE_NAISSANCE = "http://hl7.org/fhir/StructureDefinition/patient-birthPlace"
EXTENSION_NATIONALITE = "http://hl7.org/fhir/StructureDefinition/patient-nationality"
GENRES = {Sexe.FEMININ: "female", Sexe.MASCULIN: "male"}
PERSONNE_A_PREVENIR = "C"

TYPE_OFFICINE = "officine"
LIBELLES_DES_TYPES_DE_STRUCTURE = {
    Niveau.CHU_NATIONAL: "CHU national",
    Niveau.CHU_DEPARTEMENTAL: "CHU départemental",
    Niveau.CHU_DE_ZONE: "CHU de zone",
    Niveau.CENTRE_DE_SANTE: "Centre de santé",
    TYPE_OFFICINE: "Officine",
}


def _nom(nom: str, prenoms: tuple[str, ...]) -> dict[str, Any]:
    """Un nom de personne (HumanName) : le nom de famille, puis les prénoms."""
    return {"family": nom, "given": list(prenoms)}


def _telephone(numero: str) -> dict[str, str]:
    """Un numéro de téléphone (ContactPoint)."""
    return {"system": "phone", "value": numero}


def organization(structure: Etablissement | Officine) -> Ressource:
    """Un établissement ou une officine, en `Organization` : son nom, son type, sa commune.
    L'établissement porte aussi son sigle."""
    type_: str
    if isinstance(structure, Etablissement):
        type_, noms = structure.niveau, {"name": structure.nom, "alias": [structure.sigle]}
    else:
        type_, noms = TYPE_OFFICINE, {"name": structure.nom}
    return {
        "resourceType": "Organization",
        "id": structure.id,
        "active": True,
        "type": [
            {
                "coding": [
                    {
                        "system": systemes.TYPE_DE_STRUCTURE,
                        "code": type_,
                        "display": LIBELLES_DES_TYPES_DE_STRUCTURE[type_],
                    }
                ]
            }
        ],
        **noms,
        "address": [
            {"city": structure.commune, "state": structure.departement, "country": PAYS_DU_NOYAU}
        ],
    }


def practitioner(agent: Agent) -> Ressource:
    """Un agent, en `Practitioner` : son nom, et son rôle comme qualification. Son établissement n'y
    est pas : c'est celui du compte avec lequel il se connecte, que porte son jeton."""
    return {
        "resourceType": "Practitioner",
        "id": agent.id,
        "active": True,
        "name": [_nom(agent.nom, agent.prenoms)],
        "qualification": [
            {
                "code": {
                    "coding": [{"system": systemes.ROLE, "code": agent.role}],
                    "text": agent.role,
                }
            }
        ],
    }


def patient(personne: Patient) -> Ressource:
    """Un patient, en `Patient` : son NPI pour seul identifiant, son identité civile, où le joindre et
    en quelle langue lui parler. Lieu de naissance et nationalité par les extensions standard ;
    l'adresse du département (`state`) au quartier (`line`)."""
    ressource: Ressource = {
        "resourceType": "Patient",
        "id": personne.id,
        "extension": [
            {
                "url": EXTENSION_LIEU_DE_NAISSANCE,
                "valueAddress": {
                    "city": personne.lieu_de_naissance.commune,
                    "country": personne.lieu_de_naissance.pays,
                },
            },
            {
                "url": EXTENSION_NATIONALITE,
                "extension": [
                    {
                        "url": "code",
                        "valueCodeableConcept": {
                            "coding": [{"system": systemes.PAYS, "code": personne.nationalite}]
                        },
                    }
                ],
            },
        ],
        "identifier": [{"system": systemes.NPI, "value": personne.npi}],
        "active": True,
        "name": [{"use": "official", **_nom(personne.nom, personne.prenoms)}],
        "gender": GENRES[personne.sexe],
        "birthDate": personne.naissance.isoformat(),
        "address": [
            {
                "use": "home",
                "line": [personne.adresse.quartier],
                "district": personne.adresse.arrondissement,
                "city": personne.adresse.commune,
                "state": personne.adresse.departement,
                "country": PAYS_DU_NOYAU,
            }
        ],
        "communication": [
            {"language": {"coding": [{"system": systemes.LANGUE, "code": langue}]}}
            for langue in personne.langues
        ],
    }
    if personne.telephone:
        ressource["telecom"] = [_telephone(personne.telephone)]
    if contact := personne.personne_a_prevenir:
        ressource["contact"] = [
            {
                "relationship": [
                    {
                        "coding": [{"system": systemes.ROLE_DE_CONTACT, "code": PERSONNE_A_PREVENIR}],
                        "text": contact.relation,
                    }
                ],
                "name": _nom(contact.nom, contact.prenoms),
                "telecom": [_telephone(contact.telephone)],
            }
        ]
    return ressource


def charge_item_definition(tarif: Tarif) -> Ressource:
    """Un tarif, en `ChargeItemDefinition` : le produit ou l'acte en `code` (catalogue de Lafia, et ATC
    pour un médicament), son établissement en contexte d'usage `venue`, son prix en composante de base.
    Son identifiant `<établissement>:<code>` le fait trouver par une seule recherche."""
    id_ = f"tarif-{tarif.etablissement}-{tarif.produit.code}".lower()
    if not IDENTIFIANT_FHIR.fullmatch(id_):
        raise ValueError(f"identifiant de tarif hors du format FHIR : {id_}")
    produit = tarif.produit
    codes = [{"system": systemes.CATALOGUE, "code": produit.code, "display": produit.libelle}]
    if produit.atc:
        codes.append({"system": systemes.ATC, "code": produit.atc})
    return {
        "resourceType": "ChargeItemDefinition",
        "id": id_,
        "url": f"{systemes.LAFIA}/ChargeItemDefinition/{id_}",
        "identifier": [{"system": systemes.TARIF, "value": f"{tarif.etablissement}:{produit.code}"}],
        "title": produit.libelle,
        "status": "active",
        "code": {"coding": codes, "text": produit.libelle},
        "useContext": [
            {
                "code": {"system": systemes.CONTEXTE_D_USAGE, "code": "venue"},
                "valueReference": {"reference": f"Organization/{tarif.etablissement}"},
            }
        ],
        "propertyGroup": [
            {"priceComponent": [{"type": "base", "amount": {"value": tarif.prix, "currency": DEVISE}}]}
        ],
    }
