"""L'Extraction de démonstration (ADR 0009) : elle répond au contrat comme le modèle le fera, sans rien lire.

Aucun modèle de lecture n'existe encore. En attendant, chaque type de Document reçoit les mêmes
propositions, fixes, qui ressemblent à ce qu'un vrai Document de ce type porterait : de quoi faire
tourner le triage, la validation et l'écriture au dossier de bout en bout. Le modèle rendu,
`demonstration:0`, fait dire à chaque écran « extraction de démonstration ». Rien ici ne dépend des
pages reçues : les mêmes pages donnent la même Extraction.

Chaque proposition est une ressource FHIR R4 des sortes que le dossier tient déjà, sans id, sans sujet
et sans auteur : le service `relecture` les remplit à la validation. Chaque Coding porte son libellé,
chaque CodeableConcept son texte.
"""

from typing import Any

from commun.extraction import MODELE_DE_DEMONSTRATION, Extraction, Proposition
from commun.fhir import systemes

STATUT_CLINIQUE = "http://terminology.hl7.org/CodeSystem/condition-clinical"
STATUT_CLINIQUE_D_ALLERGIE = "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical"
VERIFICATION_D_ALLERGIE = "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification"
CATEGORIE_D_OBSERVATION = "http://terminology.hl7.org/CodeSystem/observation-category"

AVERTISSEMENT = (
    "Extraction de démonstration : aucun modèle n'a lu ce document. Le texte et les propositions "
    "ci-dessous sont des exemples fixes, les mêmes pour chaque document de ce type."
)


def _concept(systeme: str, code: str, libelle: str) -> dict[str, Any]:
    return {"coding": [{"system": systeme, "code": code, "display": libelle}], "text": libelle}


def _antecedent(code: str, libelle: str, cim_10: str, depuis: str, *, actif: bool) -> dict[str, Any]:
    return {
        "resourceType": "Condition",
        "category": [
            _concept(systemes.CATEGORIE_DE_CONDITION, "problem-list-item", "Antécédent"),
            _concept(systemes.TYPE_D_ANTECEDENT, "medical", "Médical"),
        ],
        "clinicalStatus": _concept(STATUT_CLINIQUE, "active" if actif else "resolved", "Actif" if actif else "Résolu"),
        "verificationStatus": _concept(systemes.VERIFICATION, "unconfirmed", "Non confirmé"),
        "code": {
            "coding": [
                {"system": systemes.DIAGNOSTIC, "code": code, "display": libelle},
                {"system": systemes.CIM_10, "code": cim_10, "display": libelle},
            ],
            "text": libelle,
        },
        "onsetString": depuis,
    }


def _allergie_a_la_penicilline() -> dict[str, Any]:
    return {
        "resourceType": "AllergyIntolerance",
        "clinicalStatus": _concept(STATUT_CLINIQUE_D_ALLERGIE, "active", "Active"),
        "verificationStatus": _concept(VERIFICATION_D_ALLERGIE, "unconfirmed", "Non confirmée"),
        "category": ["medication"],
        "code": {"coding": [{"system": systemes.ATC, "code": "J01C", "display": "Pénicillines"}], "text": "Pénicilline"},
    }


def _mesure(categorie: str, libelle_de_categorie: str, loinc: str, libelle: str, valeur: float, unite: str) -> dict[str, Any]:
    """Une mesure lue sur le papier. Sa date est celle du papier : `relecture` la tient du Document."""
    return {
        "resourceType": "Observation",
        "status": "final",
        "category": [_concept(CATEGORIE_D_OBSERVATION, categorie, libelle_de_categorie)],
        "code": _concept(systemes.LOINC, loinc, libelle),
        "valueQuantity": {"value": valeur, "unit": unite, "system": systemes.UCUM, "code": unite},
    }


def _traitement_antipaludeen() -> dict[str, Any]:
    return {
        "resourceType": "MedicationStatement",
        "status": "completed",
        "medicationCodeableConcept": {
            "coding": [{"system": systemes.ATC, "code": "P01BF01", "display": "Artéméther et luméfantrine"}],
            "text": "Artéméther-luméfantrine 20/120 mg",
        },
        "dosage": [{"text": "4 comprimés matin et soir, 3 jours"}],
    }


# Par type de Document (`commun.fhir.documents.TYPES_DE_DOCUMENT`) : les lignes du texte « lu », et les
# propositions, chacune avec la confiance du modèle et le passage du texte où il l'a lue.
EXEMPLES: dict[str, tuple[list[str], list[Proposition]]] = {
    "carnet": (
        ["Antécédents : paludisme en 2019.", "Allergie : pénicilline.", "Consultation : T° 38,5 °C."],
        [
            Proposition(
                ressource=_antecedent("paludisme", "Paludisme", "B54", "2019", actif=False),
                confiance=0.82,
                extrait="Antécédents : paludisme en 2019.",
            ),
            Proposition(ressource=_allergie_a_la_penicilline(), confiance=0.74, extrait="Allergie : pénicilline."),
            Proposition(
                ressource=_mesure("vital-signs", "Signes vitaux", "8310-5", "Température corporelle", 38.5, "Cel"),
                confiance=0.68,
                extrait="Consultation : T° 38,5 °C.",
            ),
        ],
    ),
    "resultat-analyse": (
        ["Numération formule sanguine.", "Hémoglobine : 10,2 g/dL."],
        [
            Proposition(
                ressource=_mesure("laboratory", "Laboratoire", "718-7", "Hémoglobine", 10.2, "g/dL"),
                confiance=0.86,
                extrait="Hémoglobine : 10,2 g/dL.",
            ),
        ],
    ),
    "ordonnance": (
        ["Artéméther-luméfantrine 20/120 mg : 4 comprimés matin et soir, 3 jours."],
        [
            Proposition(
                ressource=_traitement_antipaludeen(),
                confiance=0.77,
                extrait="Artéméther-luméfantrine 20/120 mg : 4 comprimés matin et soir, 3 jours.",
            ),
        ],
    ),
    "compte-rendu": (
        ["Compte rendu de consultation.", "Hypertension artérielle connue, suivie depuis 2016."],
        [
            Proposition(
                ressource=_antecedent("hta", "Hypertension artérielle", "I10", "2016", actif=True),
                confiance=0.63,
                extrait="Hypertension artérielle connue, suivie depuis 2016.",
            ),
        ],
    ),
}


def extraire(type_de_document: str) -> Extraction:
    """L'Extraction de démonstration d'un Document de ce type : un texte qui se dit exemple, et les
    propositions fixes du type ; aucune pour un type sans exemple (imagerie, certificat, autre)."""
    lignes, propositions = EXEMPLES.get(type_de_document, ([], []))
    return Extraction(
        modele=MODELE_DE_DEMONSTRATION,
        texte="\n".join([AVERTISSEMENT, "", *lignes]),
        propositions=[p.model_copy(deep=True) for p in propositions],
    )
