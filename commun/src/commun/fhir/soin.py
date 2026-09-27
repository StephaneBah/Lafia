"""Le dossier clinique écrit par le service soin, en ressources FHIR, et relu pour l'afficher.

Formes : docs/specs/F3-v1-complete.md, contrat FHIR. Chaque Coding porte son `display`, chaque
CodeableConcept son `text` : un lecteur n'a besoin d'aucun catalogue pour les afficher.
"""

import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from commun.fhir import systemes
from commun.fhir.client import Ressource
from commun.fhir.documents import origine_de
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

ALLERGIES: dict[str, str] = {
    "M01A": "Anti-inflammatoires non stéroïdiens (AINS)",
    "J01C": "Pénicillines",
    "J01E": "Sulfamides",
    "N02BA": "Aspirine et salicylés",
    "P01BC": "Quinine et apparentés",
    "N02A": "Codéine et opioïdes",
    "V08": "Iode (produits de contraste)",
}
"""Les classes ATC auxquelles une allergie se déclare : la pharmacie arrête toute ligne de la classe."""

GROUPES_SANGUINS = ("A+", "A−", "B+", "B−", "AB+", "AB−", "O+", "O−")
GROUPE_SANGUIN = ("882-1", "Groupe sanguin ABO et Rhésus")

TypeDAntecedent = Literal["medical", "chirurgical"]
TYPES_D_ANTECEDENT = {"medical": "Médical", "chirurgical": "Chirurgical", "familial": "Familial"}

LienDeParente = Literal["mere", "pere", "fratrie", "enfant", "grand-parent"]
LIENS_DE_PARENTE: dict[str, tuple[str, str]] = {
    "mere": ("MTH", "Mère"),
    "pere": ("FTH", "Père"),
    "fratrie": ("SIB", "Frère ou sœur"),
    "enfant": ("CHILD", "Enfant"),
    "grand-parent": ("GRPRN", "Grand-parent"),
}
LIENS_DES_CODES = {code: lien for lien, (code, _) in LIENS_DE_PARENTE.items()} | {
    "GRMTH": "grand-parent",
    "GRFTH": "grand-parent",
}

CATEGORIES_DE_CONDITION = {"problem-list-item": "Antécédent", "encounter-diagnosis": "Diagnostic de visite"}


def forme_du_produit(libelle: str) -> str:
    """L'unité dans laquelle un produit se compte, tirée de son libellé au catalogue."""
    texte = libelle.lower()
    for mot, forme in (
        ("comprimé", "comprimé"),
        ("gélule", "gélule"),
        ("sachet", "sachet"),
        ("sirop", "flacon"),
        ("flacon", "flacon"),
        ("injectable", "ampoule"),
        ("injection", "ampoule"),
    ):
        if mot in texte:
            return forme
    return "unité"


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
SYSTEME_VERIFICATION = systemes.VERIFICATION


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
        "category": [_categorie_de_condition("encounter-diagnosis")],
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


def _categorie_de_condition(code: str) -> dict[str, Any]:
    return _concept(systemes.CATEGORIE_DE_CONDITION, code, CATEGORIES_DE_CONDITION[code])


def antecedent(
    *, patient: str, type_: TypeDAntecedent, libelle: str, depuis: str | None, actif: bool, soignant: str
) -> Ressource:
    """Un antécédent médical ou chirurgical : une Condition de la liste des problèmes, sans visite."""
    ressource: Ressource = {
        "resourceType": "Condition",
        "category": [
            _categorie_de_condition("problem-list-item"),
            _concept(systemes.TYPE_D_ANTECEDENT, type_, TYPES_D_ANTECEDENT[type_]),
        ],
        "clinicalStatus": _concept(
            SYSTEME_STATUT_CLINIQUE, "active" if actif else "resolved", "Actif" if actif else "Résolu"
        ),
        "code": {"text": libelle},
        "subject": reference("Patient", patient),
        "recorder": reference("Practitioner", soignant),
        "recordedDate": maintenant(),
    }
    if depuis:
        ressource["onsetString"] = depuis
    return ressource


def family_member_history(*, patient: str, lien: LienDeParente, libelle: str) -> Ressource:
    """Un antécédent familial : la maladie d'un parent, par son lien au patient."""
    code, texte = LIENS_DE_PARENTE[lien]
    return {
        "resourceType": "FamilyMemberHistory",
        "status": "completed",
        "patient": reference("Patient", patient),
        "date": maintenant(),
        "relationship": _concept(systemes.LIEN_DE_PARENTE, code, texte),
        "condition": [{"code": {"text": libelle}}],
    }


def medication_statement(
    *, patient: str, tarif: Ressource | None, libelle: str, posologie: str, moments: list[str], soignant: str
) -> Ressource:
    """Un traitement au long cours : le produit du catalogue quand il y est, son texte toujours."""
    medicament: dict[str, Any] = {"text": libelle}
    if tarif is not None:
        medicament = {"coding": tarif["code"]["coding"], "text": tarif["code"].get("text") or libelle}
    return {
        "resourceType": "MedicationStatement",
        "status": "active",
        "subject": reference("Patient", patient),
        "medicationCodeableConcept": medicament,
        "dosage": [
            {"text": posologie, "timing": {"repeat": {"when": [MOMENTS[m] for m in MOMENTS if m in moments]}}}
        ],
        "effectivePeriod": {"start": maintenant()},
        "informationSource": reference("Practitioner", soignant),
        "dateAsserted": maintenant(),
    }


def arreter_traitement(traitement: Ressource) -> Ressource:
    """Le même traitement, arrêté maintenant : sa nouvelle version."""
    traitement["status"] = "stopped"
    traitement.setdefault("effectivePeriod", {})["end"] = maintenant()
    return traitement


def groupe_sanguin(*, patient: str, valeur: str, soignant: str) -> Ressource:
    """Le groupe sanguin : une Observation de laboratoire, LOINC 882-1. La plus récente fait foi."""
    code, libelle = GROUPE_SANGUIN
    return {
        "resourceType": "Observation",
        "status": "final",
        "category": [_concept(SYSTEME_CATEGORIE_OBSERVATION, "laboratory", LIBELLES_DES_CATEGORIES["laboratory"])],
        "code": _concept(systemes.LOINC, code, libelle),
        "subject": reference("Patient", patient),
        "performer": [reference("Practitioner", soignant)],
        "effectiveDateTime": maintenant(),
        "valueCodeableConcept": {"text": valeur},
    }


def clore(cas: Ressource) -> Ressource:
    """Le même cas, clos maintenant : sa nouvelle version."""
    cas["status"] = "finished"
    cas.setdefault("period", {})["end"] = maintenant()
    return cas


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
    forme = forme_du_produit(code.get("text", ""))
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
            "quantity": {"value": quantite, "unit": forme},
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
                "doseAndRate": [{"doseQuantity": {"value": dose, "unit": forme}}],
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


def nom_de(ressource: Ressource | None, repli: str = "") -> str:
    """Le nom d'un établissement ou d'une personne, tel que le noyau le tient."""
    if not ressource:
        return repli
    if ressource.get("resourceType") == "Organization":
        return ressource.get("name") or repli
    return nom_de_personne(ressource) or repli


def age(naissance: str | None, aujourd_hui: date | None = None) -> int | None:
    """L'âge révolu, en années, d'une date de naissance FHIR (`AAAA`, `AAAA-MM` ou `AAAA-MM-JJ`)."""
    if not naissance:
        return None
    parties = [int(p) for p in naissance.split("-")]
    annee, mois, jour = (parties + [1, 1])[:3]
    jour_j = aujourd_hui or date.today()
    return jour_j.year - annee - ((jour_j.month, jour_j.day) < (mois, jour))


def resume_patient(patient: Ressource) -> dict[str, Any]:
    nom = patient.get("name", [{}])[0]
    return {
        "id": patient["id"],
        "npi": next((i["value"] for i in patient.get("identifier", []) if i.get("system") == systemes.NPI), None),
        "age": age(patient.get("birthDate")),
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
        "origine": origine_de(allergie),
    }


def motif_du_cas(cas: Ressource) -> str:
    return (cas.get("type") or [{}])[0].get("text", "")


def cas_actif(cas: Ressource) -> bool:
    return cas.get("status") == "active"


def statut_du_cas(cas: Ressource) -> str:
    return "en-cours" if cas_actif(cas) else "termine"


def debut(ressource: Ressource) -> str:
    return ressource.get("period", {}).get("start", "")


def fin(ressource: Ressource) -> str | None:
    return ressource.get("period", {}).get("end")


def patient_du_cas(cas: Ressource) -> str | None:
    return id_de(cas.get("patient"))


def etablissement_du_cas(cas: Ressource) -> str | None:
    return id_de(cas.get("managingOrganization"))


def etablissement_de_la_visite(visite: Ressource) -> str | None:
    return id_de(visite.get("serviceProvider"))


def cas_de_la_visite(visite: Ressource) -> set[str]:
    return {i for e in visite.get("episodeOfCare", []) if (i := id_de(e))}


def visite_d_urgence(visite: Ressource) -> bool:
    return visite.get("class", {}).get("code") == "EMER"


def motif_de_la_visite(visite: Ressource) -> str:
    return (visite.get("reasonCode") or [{}])[0].get("text", "")


def soignant_de_la_visite(visite: Ressource) -> dict[str, str] | None:
    return (visite.get("participant") or [{}])[0].get("individual")


def visite_de(ressource: Ressource) -> str | None:
    """La visite où une mesure, un diagnostic ou une ligne a été écrit ; None pour ce qui n'en a pas."""
    return id_de(ressource.get("encounter"))


def _codes_de_categorie(ressource: Ressource) -> set[str]:
    return {c.get("code") for cat in ressource.get("category", []) for c in cat.get("coding", [])}


def est_antecedent(condition: Ressource) -> bool:
    """Un antécédent porte `problem-list-item` ; un diagnostic `encounter-diagnosis` (ou rien, avant F4)."""
    return "problem-list-item" in _codes_de_categorie(condition)


def est_groupe_sanguin(observation: Ressource) -> bool:
    return any(
        c.get("system") == systemes.LOINC and c.get("code") == GROUPE_SANGUIN[0]
        for c in observation.get("code", {}).get("coding", [])
    )


def valeur_du_groupe_sanguin(observations: list[Ressource]) -> str | None:
    """La valeur du groupe sanguin le plus récent, ou None."""
    groupes = sorted(
        (o for o in observations if est_groupe_sanguin(o)), key=lambda o: o.get("effectiveDateTime", "")
    )
    return groupes[-1].get("valueCodeableConcept", {}).get("text") if groupes else None


def resume_antecedent(condition: Ressource) -> dict[str, Any]:
    type_ = next(
        (
            c["code"]
            for cat in condition.get("category", [])
            for c in cat.get("coding", [])
            if c.get("system") == systemes.TYPE_D_ANTECEDENT
        ),
        "medical",
    )
    return {
        "id": condition.get("id"),
        "type": type_,
        "libelle": condition.get("code", {}).get("text", ""),
        "depuis": condition.get("onsetString"),
        "actif": any(c.get("code") == "active" for c in condition.get("clinicalStatus", {}).get("coding", [])),
        "origine": origine_de(condition),
    }


def resume_familial(historique: Ressource) -> dict[str, Any]:
    lien = historique.get("relationship", {})
    code = next((c.get("code") for c in lien.get("coding", [])), "")
    return {
        "id": historique.get("id"),
        "lien": LIENS_DES_CODES.get(code, lien.get("text", "")),
        "libelle": (historique.get("condition") or [{}])[0].get("code", {}).get("text", ""),
        "origine": origine_de(historique),
    }


def traitement_actif(traitement: Ressource) -> bool:
    return traitement.get("status") == "active"


def patient_du_traitement(traitement: Ressource) -> str | None:
    return id_de(traitement.get("subject"))


def resume_traitement(traitement: Ressource) -> dict[str, Any]:
    dosage = (traitement.get("dosage") or [{}])[0]
    quand = dosage.get("timing", {}).get("repeat", {}).get("when", [])
    return {
        "id": traitement.get("id"),
        "libelle": traitement.get("medicationCodeableConcept", {}).get("text", ""),
        "produit": code_du_catalogue(traitement, "medicationCodeableConcept"),
        "posologie": dosage.get("text", ""),
        "moments": [MOMENTS_DES_TIMINGS[w] for w in quand if w in MOMENTS_DES_TIMINGS],
        "depuis": traitement.get("effectivePeriod", {}).get("start"),
        "actif": traitement_actif(traitement),
        "origine": origine_de(traitement),
    }


def series_de_mesures(observations: list[Ressource]) -> dict[str, list[dict[str, Any]]]:
    """Les mesures chiffrées des visites, par code LOINC et dans l'ordre du temps : de quoi tracer une courbe."""
    series: dict[str, list[dict[str, Any]]] = {}
    for o in sorted(observations, key=lambda o: o.get("effectiveDateTime", "")):
        valeur = o.get("valueQuantity", {}).get("value")
        if visite_de(o) is None or not isinstance(valeur, int | float):
            continue
        code = next(
            (c["code"] for c in o.get("code", {}).get("coding", []) if c.get("system") == systemes.LOINC), None
        )
        if code:
            series.setdefault(code, []).append({"date": o.get("effectiveDateTime"), "valeur": valeur})
    return series


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
        "unite": ligne.get("dispenseRequest", {}).get("quantity", {}).get("unit"),
        "dose": dose,
        "moments": [MOMENTS_DES_TIMINGS[w] for w in repeat.get("when", []) if w in MOMENTS_DES_TIMINGS],
        "jours": repeat.get("boundsDuration", {}).get("value"),
        "posologie": dosage.get("text", ""),
    }
