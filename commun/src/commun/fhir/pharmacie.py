"""Ce que la pharmacie lit et écrit au noyau : les lignes d'une ordonnance, leur paiement, les
allergies du patient, et la délivrance.

Les formes sont le contrat de docs/specs/F3-v1-complete.md : lignes en `MedicationRequest`,
encaissement en `Invoice`, allergie en `AllergyIntolerance`, délivrance en `MedicationDispense`.
Ce module traduit ; ce que la pharmacie décide vit dans `services/pharmacie/regles/`.
"""

from dataclasses import dataclass, field
from typing import Any

from commun.fhir import systemes
from commun.fhir.client import ClientFhir, Ressource
from commun.fhir.dossier import id_de, maintenant, reference

# Les moments de prise de FHIR (`systemes.MOMENT_DE_PRISE`), en mots de Lafia.
MOMENTS = {"MORN": "matin", "NOON": "midi", "EVE": "soir", "NIGHT": "nuit"}


@dataclass(frozen=True)
class Posologie:
    moments: list[str]
    jours: int | None
    dose: float | None
    texte: str | None


@dataclass(frozen=True)
class Ligne:
    """Une ligne d'ordonnance, lue de son `MedicationRequest`."""

    id: str
    code: str | None
    """Le code du catalogue de Lafia : `MED-IBUPROFENE-400`, `ACT-CONSULTATION`."""
    atc: str | None
    libelle: str
    prescrite: int
    etablissement: str | None
    """L'établissement où elle se sert : `dispenseRequest.performer`."""
    patient: str | None
    prescripteur: str | None
    date: str | None
    posologie: Posologie
    medicament: dict[str, Any] = field(repr=False)
    """Son `medicationCodeableConcept`, que la délivrance reprend tel quel."""


@dataclass(frozen=True)
class Allergie:
    libelle: str
    atc: list[str]


def _code(concept: dict[str, Any], systeme: str) -> str | None:
    return next((c.get("code") for c in concept.get("coding", []) if c.get("system") == systeme), None)


def _libelle(concept: dict[str, Any]) -> str:
    if concept.get("text"):
        return str(concept["text"])
    return next((str(c["display"]) for c in concept.get("coding", []) if c.get("display")), "Produit")


def _entier(valeur: object) -> int:
    try:
        return int(float(valeur))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def _posologie(ressource: Ressource) -> Posologie:
    dosage = (ressource.get("dosageInstruction") or [{}])[0]
    repetition = dosage.get("timing", {}).get("repeat", {})
    moments = [MOMENTS[m] for m in repetition.get("when", []) if m in MOMENTS]
    duree = repetition.get("boundsDuration", {}).get("value")
    dose = (dosage.get("doseAndRate") or [{}])[0].get("doseQuantity", {}).get("value")
    return Posologie(
        moments=moments,
        jours=_entier(duree) or None,
        dose=float(dose) if isinstance(dose, (int, float)) else None,
        texte=dosage.get("text"),
    )


def ligne(ressource: Ressource) -> Ligne:
    """Une ligne d'ordonnance, depuis son `MedicationRequest`."""
    medicament = ressource.get("medicationCodeableConcept", {})
    demande = ressource.get("dispenseRequest", {})
    return Ligne(
        id=ressource["id"],
        code=_code(medicament, systemes.CATALOGUE),
        atc=_code(medicament, systemes.ATC),
        libelle=_libelle(medicament),
        prescrite=_entier(demande.get("quantity", {}).get("value")),
        etablissement=id_de(demande.get("performer")),
        patient=id_de(ressource.get("subject")),
        prescripteur=id_de(ressource.get("requester")),
        date=ressource.get("authoredOn"),
        posologie=_posologie(ressource),
        medicament=medicament,
    )


async def lignes_de_l_ordonnance(fhir: ClientFhir, numero: str) -> list[Ligne]:
    """Les lignes qui portent ce numéro d'ordonnance : `MedicationRequest.groupIdentifier`."""
    trouves = await fhir.chercher("MedicationRequest", {"identifier": f"{systemes.ORDONNANCE}|{numero}"})
    return [ligne(r) for r in trouves if r.get("resourceType") == "MedicationRequest"]


async def lignes_payees(fhir: ClientFhir, numero: str) -> set[str]:
    """Les identifiants des lignes qu'un encaissement de cette ordonnance porte."""
    encaissements = await fhir.chercher("Invoice", {"identifier": f"{systemes.ORDONNANCE}|{numero}"})
    return {
        coding["code"]
        for encaissement in encaissements
        if encaissement.get("status") != "cancelled"
        for item in encaissement.get("lineItem", [])
        for coding in item.get("chargeItemCodeableConcept", {}).get("coding", [])
        if coding.get("system") == systemes.LIGNE and coding.get("code")
    }


async def quantite_remise(fhir: ClientFhir, ligne_id: str) -> int:
    """Ce qui a été remis de cette ligne : la somme de ses `MedicationDispense.quantity`."""
    delivrances = await fhir.chercher("MedicationDispense", {"prescription": f"MedicationRequest/{ligne_id}"})
    return sum(
        _entier(d.get("quantity", {}).get("value"))
        for d in delivrances
        if d.get("resourceType") == "MedicationDispense" and d.get("status") == "completed"
    )


async def allergies_du_patient(fhir: ClientFhir, patient: str) -> list[Allergie]:
    """Les allergies du patient, chacune avec ses codes ATC."""
    trouvees = await fhir.chercher("AllergyIntolerance", {"patient": f"Patient/{patient}"})
    allergies = []
    for allergie in trouvees:
        code = allergie.get("code", {})
        atc = [c["code"] for c in code.get("coding", []) if c.get("system") == systemes.ATC and c.get("code")]
        if atc:
            allergies.append(Allergie(libelle=_libelle(code), atc=atc))
    return allergies


@dataclass(frozen=True)
class TraitementAuLongCours:
    libelle: str
    posologie: str


async def traitements_au_long_cours(fhir: ClientFhir, patient: str) -> list[TraitementAuLongCours]:
    """Les traitements au long cours en cours du patient (MedicationStatement actifs), que le pharmacien
    voit avant de remettre : une interaction se repère au comptoir."""
    trouves = await fhir.chercher("MedicationStatement", {"subject": f"Patient/{patient}", "status": "active"})
    return [
        TraitementAuLongCours(
            libelle=_libelle(t.get("medicationCodeableConcept", {})),
            posologie=(t.get("dosage") or [{}])[0].get("text", ""),
        )
        for t in trouves
    ]


def _nom(ressource: Ressource | None) -> tuple[str, str]:
    """Le nom de famille et les prénoms d'un Patient ou d'un Practitioner."""
    if not ressource or not ressource.get("name"):
        return "", ""
    nom = ressource["name"][0]
    return nom.get("family", ""), " ".join(nom.get("given", []))


async def nom_du_patient(fhir: ClientFhir, patient: str) -> tuple[str, str]:
    return _nom(await fhir.lire("Patient", patient))


async def nom_du_prescripteur(fhir: ClientFhir, practitioner: str | None) -> str | None:
    if not practitioner:
        return None
    nom, prenoms = _nom(await fhir.lire("Practitioner", practitioner))
    return " ".join(p for p in (prenoms, nom) if p) or None


def _delivrance(ligne: Ligne, quantite: int, performers: list[dict[str, str]]) -> Ressource:
    medicament = dict(ligne.medicament)
    medicament.setdefault("text", ligne.libelle)
    ressource: Ressource = {
        "resourceType": "MedicationDispense",
        "status": "completed",
        "medicationCodeableConcept": medicament,
        "authorizingPrescription": [reference("MedicationRequest", ligne.id)],
        "quantity": {"value": quantite},
        "performer": [{"actor": acteur} for acteur in performers],
        "whenHandedOver": maintenant(),
    }
    if ligne.patient:
        ressource["subject"] = reference("Patient", ligne.patient)
    return ressource


def medication_dispense(ligne: Ligne, quantite: int, pharmacien: str, etablissement: str) -> Ressource:
    """La remise de `quantite` unités de `ligne` au comptoir d'un établissement, en `MedicationDispense`."""
    return _delivrance(
        ligne, quantite, [reference("Practitioner", pharmacien), reference("Organization", etablissement)]
    )


def vente_d_officine(ligne: Ligne, quantite: int, officine: str) -> Ressource:
    """La vente de `quantite` unités de `ligne` par une officine, en `MedicationDispense` : son seul
    `performer` est l'Organization de l'officine, dont les pharmaciens n'ont pas de compte."""
    return _delivrance(ligne, quantite, [reference("Organization", officine)])


async def nom_de_l_organisation(fhir: ClientFhir, organisation: str | None) -> str | None:
    """Le nom d'un établissement ou d'une officine, `Organization.name`."""
    if not organisation:
        return None
    ressource = await fhir.lire("Organization", organisation)
    return str(ressource["name"]) if ressource and ressource.get("name") else None
