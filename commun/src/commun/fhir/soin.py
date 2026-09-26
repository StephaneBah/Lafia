"""Le dossier clinique écrit par le service soin, en ressources FHIR, et relu pour l'afficher.

Formes : docs/specs/F3-v1-complete.md, contrat FHIR. Chaque Coding porte son `display`, chaque
CodeableConcept son `text` : un lecteur n'a besoin d'aucun catalogue pour les afficher.
"""

import uuid
from dataclasses import dataclass
from typing import Any, Literal

from commun.fhir import systemes
from commun.fhir.client import Ressource
from commun.fhir.dossier import id_de, maintenant, reference

# Catalogues : ce qu'un soignant choisit, jamais ce qu'il tape.


@dataclass(frozen=True)
class Mesure:
    code: str
    """Code LOINC de la mesure : c'est aussi son code dans l'API du service."""
    libelle: str
    unite: str
    """Unité UCUM ; `positif/négatif` pour un TDR."""
    categorie: Literal["vital-signs", "laboratory"]
    forme: Literal["quantite", "tension", "tdr"] = "quantite"


MESURES: dict[str, Mesure] = {
    m.code: m
    for m in (
        Mesure("8310-5", "Température", "Cel", "vital-signs"),
        Mesure("85354-9", "Tension artérielle", "mm[Hg]", "vital-signs", "tension"),
        Mesure("8867-4", "Pouls", "/min", "vital-signs"),
        Mesure("29463-7", "Poids", "kg", "vital-signs"),
        Mesure("59408-5", "Saturation en oxygène (SpO2)", "%", "vital-signs"),
        Mesure("2339-0", "Glycémie", "g/L", "laboratory"),
        Mesure("70569-9", "TDR paludisme", "positif/négatif", "laboratory", "tdr"),
        Mesure("718-7", "Hémoglobine", "g/dL", "laboratory"),
    )
}
SYSTOLIQUE = ("8480-6", "Pression systolique")
DIASTOLIQUE = ("8462-4", "Pression diastolique")
RESULTATS_TDR = {"positif": "Positif", "négatif": "Négatif"}
LIBELLES_DES_CATEGORIES = {"vital-signs": "Signes vitaux", "laboratory": "Laboratoire"}
SYSTEME_CATEGORIE_OBSERVATION = "http://terminology.hl7.org/CodeSystem/observation-category"


@dataclass(frozen=True)
class Diagnostic:
    code: str
    libelle: str
    cim_10: str


DIAGNOSTICS: dict[str, Diagnostic] = {
    d.code: d
    for d in (
        Diagnostic("paludisme", "Paludisme", "B54"),
        Diagnostic("ira", "Infection respiratoire aiguë", "J06.9"),
        Diagnostic("hta", "Hypertension artérielle", "I10"),
        Diagnostic("diabete", "Diabète de type 2", "E11"),
        Diagnostic("gastro-enterite", "Gastro-entérite", "A09"),
        Diagnostic("anemie", "Anémie", "D64.9"),
        Diagnostic("fievre", "Fièvre", "R50.9"),
        Diagnostic("autre", "Autre", "R69"),
    )
}

TypeDeVisite = Literal["consultation", "soins-infirmiers", "continuite", "urgence"]
TYPES_DE_VISITE: dict[str, str] = {
    "consultation": "Consultation",
    "soins-infirmiers": "Soins infirmiers",
    "continuite": "Visite de continuité",
    "urgence": "Accès d'urgence",
}

Moment = Literal["matin", "midi", "soir", "nuit"]
MOMENTS: dict[str, str] = {"matin": "MORN", "midi": "NOON", "soir": "EVE", "nuit": "NIGHT"}
LIBELLES_DES_TIMINGS = {"MORN": "Matin", "NOON": "Midi", "EVE": "Soir", "NIGHT": "Nuit"}
MOMENTS_DES_TIMINGS = {v: k for k, v in MOMENTS.items()}

SYSTEME_CLASSE = "http://terminology.hl7.org/CodeSystem/v3-ActCode"
CLASSES = {"AMB": "ambulatory", "EMER": "emergency"}
SYSTEME_STATUT_CLINIQUE = "http://terminology.hl7.org/CodeSystem/condition-clinical"
SYSTEME_VERIFICATION = "http://terminology.hl7.org/CodeSystem/condition-ver-status"


def nouvel_id(prefixe: str) -> str:
    """Un identifiant de ressource choisi par le service : l'écriture d'une visite part en une
    transaction, où chaque ressource doit connaître celles qu'elle cite."""
    return f"{prefixe}-{uuid.uuid4().hex}"


# Écriture


def episode_of_care(*, patient: str, etablissement: str, soignant: str, motif: str) -> Ressource:
    """Un cas de visite ouvert : `motif` en `type[0].text`."""
    return {
        "resourceType": "EpisodeOfCare",
        "id": nouvel_id("cas"),
        "status": "active",
        "type": [{"text": motif}],
        "patient": reference("Patient", patient),
        "managingOrganization": reference("Organization", etablissement),
        "careManager": reference("Practitioner", soignant),
        "period": {"start": maintenant()},
    }


def encounter(
    *, patient: str, cas: str, etablissement: str, soignant: str, type_: TypeDeVisite, motif: str
) -> Ressource:
    classe = "EMER" if type_ == "urgence" else "AMB"
    return {
        "resourceType": "Encounter",
        "id": nouvel_id("visite"),
        "status": "finished",
        "class": {"system": SYSTEME_CLASSE, "code": classe, "display": CLASSES[classe]},
        "type": [
            {
                "coding": [{"system": systemes.TYPE_DE_VISITE, "code": type_, "display": TYPES_DE_VISITE[type_]}],
                "text": TYPES_DE_VISITE[type_],
            }
        ],
        "subject": reference("Patient", patient),
        "episodeOfCare": [reference("EpisodeOfCare", cas)],
        "participant": [{"individual": reference("Practitioner", soignant)}],
        "serviceProvider": reference("Organization", etablissement),
        "period": {"start": maintenant()},
        "reasonCode": [{"text": motif}],
    }


def _concept(systeme: str, code: str, libelle: str) -> dict[str, Any]:
    return {"coding": [{"system": systeme, "code": code, "display": libelle}], "text": libelle}


def observation(
    *, mesure: Mesure, valeur: float | str, valeur2: float | None, patient: str, visite: str, soignant: str
) -> Ressource:
    """Une mesure : quantité UCUM, tension en deux composantes, ou TDR positif/négatif."""
    ressource: Ressource = {
        "resourceType": "Observation",
        "id": nouvel_id("mesure"),
        "status": "final",
        "category": [
            _concept(SYSTEME_CATEGORIE_OBSERVATION, mesure.categorie, LIBELLES_DES_CATEGORIES[mesure.categorie])
        ],
        "code": _concept(systemes.LOINC, mesure.code, mesure.libelle),
        "subject": reference("Patient", patient),
        "encounter": reference("Encounter", visite),
        "effectiveDateTime": maintenant(),
        "performer": [reference("Practitioner", soignant)],
    }
    if mesure.forme == "tension":
        ressource["component"] = [
            {
                "code": _concept(systemes.LOINC, code, libelle),
                "valueQuantity": _quantite(v, mesure.unite),
            }
            for (code, libelle), v in ((SYSTOLIQUE, valeur), (DIASTOLIQUE, valeur2))
        ]
    elif mesure.forme == "tdr":
        resultat = str(valeur)
        ressource["valueCodeableConcept"] = _concept(f"{systemes.LAFIA}/CodeSystem/resultat-tdr", resultat, RESULTATS_TDR[resultat])
    else:
        ressource["valueQuantity"] = _quantite(valeur, mesure.unite)
    return ressource


def _quantite(valeur: object, unite: str) -> dict[str, Any]:
    return {"value": valeur, "unit": unite, "system": systemes.UCUM, "code": unite}


def condition(
    *, diagnostic: Diagnostic, confirme: bool, note: str | None, patient: str, visite: str, soignant: str
) -> Ressource:
    verification = "confirmed" if confirme else "provisional"
    ressource: Ressource = {
        "resourceType": "Condition",
        "id": nouvel_id("diagnostic"),
        "clinicalStatus": _concept(SYSTEME_STATUT_CLINIQUE, "active", "Actif"),
        "verificationStatus": _concept(SYSTEME_VERIFICATION, verification, "Confirmé" if confirme else "Provisoire"),
        "code": {
            "coding": [
                {"system": systemes.DIAGNOSTIC, "code": diagnostic.code, "display": diagnostic.libelle},
                {"system": systemes.CIM_10, "code": diagnostic.cim_10, "display": diagnostic.libelle},
            ],
            "text": diagnostic.libelle,
        },
        "subject": reference("Patient", patient),
        "encounter": reference("Encounter", visite),
        "recorder": reference("Practitioner", soignant),
        "recordedDate": maintenant(),
    }
    if note:
        ressource["note"] = [{"text": note}]
    return ressource


def allergy_intolerance(*, patient: str, code_atc: str, libelle: str, soignant: str) -> Ressource:
    return {
        "resourceType": "AllergyIntolerance",
        "clinicalStatus": _concept(
            "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical", "active", "Active"
        ),
        "code": _concept(systemes.ATC, code_atc, libelle),
        "patient": reference("Patient", patient),
        "recorder": reference("Practitioner", soignant),
        "recordedDate": maintenant(),
    }


def texte_de_posologie(dose: float, moments: list[str], jours: int) -> str:
    dose_lisible = f"{dose:g}".replace(".", ",")
    quand = ", ".join(m for m in MOMENTS if m in moments)
    return f"{dose_lisible} {quand} · {jours} jour{'s' if jours > 1 else ''}"


def medication_request(
    *,
    tarif: Ressource,
    quantite: int,
    dose: float,
    moments: list[str],
    jours: int,
    numero: str,
    patient: str,
    visite: str,
    soignant: str,
    etablissement: str,
) -> Ressource:
    """Une ligne d'ordonnance : le produit tel que le tarif de l'établissement le nomme (catalogue et ATC)."""
    code = tarif["code"]
    timings = [MOMENTS[m] for m in MOMENTS if m in moments]
    return {
        "resourceType": "MedicationRequest",
        "id": nouvel_id("ligne"),
        "status": "active",
        "intent": "order",
        "identifier": [{"system": systemes.ORDONNANCE, "value": numero}],
        "groupIdentifier": {"system": systemes.ORDONNANCE, "value": numero},
        "medicationCodeableConcept": {"coding": code["coding"], "text": code.get("text", "")},
        "subject": reference("Patient", patient),
        "encounter": reference("Encounter", visite),
        "requester": reference("Practitioner", soignant),
        "authoredOn": maintenant(),
        "dispenseRequest": {
            "performer": reference("Organization", etablissement),
            "quantity": {"value": quantite},
        },
        "dosageInstruction": [
            {
                "text": texte_de_posologie(dose, moments, jours),
                "timing": {
                    "repeat": {
                        "when": timings,
                        "boundsDuration": {"value": jours, "unit": "d", "system": systemes.UCUM, "code": "d"},
                    }
                },
                "doseAndRate": [{"doseQuantity": {"value": dose}}],
            }
        ],
    }


# Lecture


def code_du_catalogue(ressource: Ressource, chemin: str = "code") -> str | None:
    return next(
        (c["code"] for c in ressource.get(chemin, {}).get("coding", []) if c.get("system") == systemes.CATALOGUE),
        None,
    )


def code_atc(ressource: Ressource, chemin: str = "code") -> str | None:
    return next(
        (c["code"] for c in ressource.get(chemin, {}).get("coding", []) if c.get("system") == systemes.ATC),
        None,
    )


def prix_du_tarif(tarif: Ressource) -> float:
    return float(tarif["propertyGroup"][0]["priceComponent"][0]["amount"]["value"])


def etablissement_du_tarif(tarif: Ressource) -> str | None:
    return next((id_de(u.get("valueReference")) for u in tarif.get("useContext", [])), None)


def nom_de_personne(ressource: Ressource | None) -> str:
    if not ressource or not ressource.get("name"):
        return ""
    nom = ressource["name"][0]
    return " ".join([*nom.get("given", []), nom.get("family", "")]).strip()


def resume_patient(patient: Ressource) -> dict[str, Any]:
    nom = patient.get("name", [{}])[0]
    return {
        "id": patient["id"],
        "nom": nom.get("family", ""),
        "prenoms": " ".join(nom.get("given", [])),
        "sexe": {"female": "féminin", "male": "masculin"}.get(patient.get("gender", ""), ""),
        "naissance": patient.get("birthDate"),
    }


def resume_allergie(allergie: Ressource) -> dict[str, Any]:
    code = allergie.get("code", {})
    return {
        "id": allergie.get("id"),
        "libelle": code.get("text") or next((c.get("display") for c in code.get("coding", [])), ""),
        "code_atc": next((c["code"] for c in code.get("coding", []) if c.get("system") == systemes.ATC), None),
    }


def motif_du_cas(cas: Ressource) -> str:
    return (cas.get("type") or [{}])[0].get("text", "")


def type_de_visite(visite: Ressource) -> str:
    return next(
        (c["code"] for t in visite.get("type", []) for c in t.get("coding", []) if c.get("system") == systemes.TYPE_DE_VISITE),
        "consultation",
    )


def _nombre(valeur: object) -> str:
    """Un nombre à la française : `38,5`, `130`."""
    return (f"{valeur:g}" if isinstance(valeur, int | float) else str(valeur)).replace(".", ",")


def resume_mesure(observation: Ressource) -> dict[str, Any]:
    code = next((c["code"] for c in observation["code"].get("coding", []) if c.get("system") == systemes.LOINC), "")
    mesure = MESURES.get(code)
    libelle = observation["code"].get("text") or (mesure.libelle if mesure else code)
    if "component" in observation:
        valeurs = [_nombre(c.get("valueQuantity", {}).get("value", "")) for c in observation["component"]]
        texte, unite = "/".join(valeurs), observation["component"][0].get("valueQuantity", {}).get("unit", "")
    elif "valueCodeableConcept" in observation:
        texte, unite = observation["valueCodeableConcept"].get("text", ""), ""
    else:
        quantite = observation.get("valueQuantity", {})
        texte, unite = _nombre(quantite.get("value", "")), quantite.get("unit", "")
    return {
        "id": observation.get("id"),
        "code": code,
        "libelle": libelle,
        "valeur": texte,
        "unite": unite,
        "date": observation.get("effectiveDateTime"),
    }


def resume_diagnostic(condition: Ressource) -> dict[str, Any]:
    code = condition.get("code", {})
    return {
        "id": condition.get("id"),
        "code": next((c["code"] for c in code.get("coding", []) if c.get("system") == systemes.DIAGNOSTIC), ""),
        "libelle": code.get("text", ""),
        "confirme": any(
            c.get("code") == "confirmed" for c in condition.get("verificationStatus", {}).get("coding", [])
        ),
        "note": (condition.get("note") or [{}])[0].get("text"),
    }


def numero_de_la_ligne(ligne: Ressource) -> str | None:
    groupe = ligne.get("groupIdentifier", {})
    return groupe.get("value") if groupe.get("system") == systemes.ORDONNANCE else None


def resume_ligne(ligne: Ressource) -> dict[str, Any]:
    dosage = (ligne.get("dosageInstruction") or [{}])[0]
    repeat = dosage.get("timing", {}).get("repeat", {})
    dose = (dosage.get("doseAndRate") or [{}])[0].get("doseQuantity", {}).get("value")
    return {
        "id": ligne.get("id"),
        "produit": code_du_catalogue(ligne, "medicationCodeableConcept"),
        "libelle": ligne.get("medicationCodeableConcept", {}).get("text", ""),
        "quantite": ligne.get("dispenseRequest", {}).get("quantity", {}).get("value"),
        "dose": dose,
        "moments": [MOMENTS_DES_TIMINGS[w] for w in repeat.get("when", []) if w in MOMENTS_DES_TIMINGS],
        "jours": repeat.get("boundsDuration", {}).get("value"),
        "posologie": dosage.get("text", ""),
    }
