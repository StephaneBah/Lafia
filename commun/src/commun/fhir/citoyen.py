"""Le dossier d'un patient tel que son carnet le lit : les ressources du contrat F3, traduites en choses.

Le service citoyen lit ici ce que soin, caisse et pharmacie écrivent (docs/specs/F3-v1-complete.md,
contrat FHIR) ; ses règles (`citoyen.regles`) en font les écrans du carnet. Rien n'est écrit ici, hors
de l'`AuditEvent` que chaque lecture laisse (`commun.fhir.dossier.tracer`).
"""

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from commun.fhir import systemes
from commun.fhir.client import ClientFhir, Ressource
from commun.fhir.dossier import id_de

MOMENTS = {"MORN": "matin", "NOON": "midi", "EVE": "soir", "NIGHT": "nuit"}


@dataclass(frozen=True)
class Cas:
    id: str
    motif: str
    en_cours: bool
    debut: str
    fin: str | None
    etablissement: str | None


@dataclass(frozen=True)
class Visite:
    id: str
    cas: str | None
    date: str
    type: str
    urgence: bool
    etablissement: str | None
    soignant: str | None
    motif: str | None


@dataclass(frozen=True)
class Mesure:
    visite: str | None
    loinc: str | None
    libelle: str
    valeur: float | None = None
    unite: str | None = None
    systolique: float | None = None
    diastolique: float | None = None
    resultat: str | None = None


@dataclass(frozen=True)
class Diagnostic:
    visite: str | None
    libelle: str
    confirme: bool
    gueri: bool
    note: str | None


@dataclass(frozen=True)
class Ligne:
    id: str
    numero: str | None
    visite: str | None
    code: str | None
    produit: str
    date: str
    moments: tuple[str, ...]
    par_prise: float | None
    jours: int | None
    quantite: float | None
    unite: str | None
    etablissement: str | None
    prescripteur: str | None


@dataclass(frozen=True)
class Acces:
    date: str
    qui: str | None
    """La référence de qui a ouvert le dossier : `Practitioner/…`, `Organization/…` ou `Patient/…`."""
    etablissement: str | None
    service: str | None
    motif: str | None
    raison: str | None


@dataclass
class DossierDuCitoyen:
    patient: Ressource
    cas: list[Cas] = field(default_factory=list)
    visites: list[Visite] = field(default_factory=list)
    mesures: list[Mesure] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    lignes: list[Ligne] = field(default_factory=list)
    payees: set[str] = field(default_factory=set)
    """Les lignes qu'un encaissement porte, par l'identifiant de leur MedicationRequest."""
    remis: dict[str, float] = field(default_factory=dict)
    """La quantité remise de chaque ligne : la somme de ses délivrances."""
    allergies: list[str] = field(default_factory=list)
    acces: list[Acces] = field(default_factory=list)
    noms: dict[str, str] = field(default_factory=dict)
    """Le nom de chaque soignant (`Practitioner/…`) et établissement (`Organization/…`) cité."""
    roles: dict[str, str] = field(default_factory=dict)
    """Le rôle de chaque soignant cité, par sa référence."""

    @property
    def prenom(self) -> str:
        nom = (self.patient.get("name") or [{}])[0]
        return (nom.get("given") or [""])[0]

    @property
    def nom(self) -> str:
        return (self.patient.get("name") or [{}])[0].get("family", "")


def _code(concept: dict | None, systeme: str) -> str | None:
    return next((c.get("code") for c in (concept or {}).get("coding", []) if c.get("system") == systeme), None)


def _texte(concept: dict | None) -> str | None:
    if not concept:
        return None
    return concept.get("text") or next((c.get("display") for c in concept.get("coding", []) if c.get("display")), None)


def _cas(r: Ressource) -> Cas:
    return Cas(
        id=r["id"],
        motif=_texte((r.get("type") or [None])[0]) or "Cas de visite",
        en_cours=r.get("status") != "finished",
        debut=r.get("period", {}).get("start", ""),
        fin=r.get("period", {}).get("end"),
        etablissement=(r.get("managingOrganization") or {}).get("reference"),
    )


def _visite(r: Ressource) -> Visite:
    type_ = _code((r.get("type") or [None])[0], systemes.TYPE_DE_VISITE) or "consultation"
    return Visite(
        id=r["id"],
        cas=id_de((r.get("episodeOfCare") or [None])[0]),
        date=r.get("period", {}).get("start", ""),
        type=type_,
        urgence=type_ == "urgence" or r.get("class", {}).get("code") == "EMER",
        etablissement=(r.get("serviceProvider") or {}).get("reference"),
        soignant=((r.get("participant") or [{}])[0].get("individual") or {}).get("reference"),
        motif=_texte((r.get("reasonCode") or [None])[0]),
    )


def _mesure(r: Ressource) -> Mesure:
    code = r.get("code", {})
    loinc = _code(code, systemes.LOINC)
    base = {"visite": id_de(r.get("encounter")), "loinc": loinc, "libelle": _texte(code) or "Mesure"}
    if "valueQuantity" in r:
        q = r["valueQuantity"]
        return Mesure(**base, valeur=q.get("value"), unite=q.get("unit") or q.get("code"))
    if "component" in r:
        valeurs = {_code(c.get("code"), systemes.LOINC): c.get("valueQuantity", {}).get("value") for c in r["component"]}
        return Mesure(**base, systolique=valeurs.get("8480-6"), diastolique=valeurs.get("8462-4"))
    return Mesure(**base, resultat=_texte(r.get("valueCodeableConcept")))


def _diagnostic(r: Ressource) -> Diagnostic:
    code = r.get("code", {})
    return Diagnostic(
        visite=id_de(r.get("encounter")),
        libelle=_texte(code) or _code(code, systemes.DIAGNOSTIC) or "Diagnostic",
        confirme=_code(r.get("verificationStatus"), "http://terminology.hl7.org/CodeSystem/condition-ver-status") == "confirmed",
        gueri=_code(r.get("clinicalStatus"), "http://terminology.hl7.org/CodeSystem/condition-clinical") in ("resolved", "inactive"),
        note=((r.get("note") or [{}])[0]).get("text"),
    )


def _ligne(r: Ressource) -> Ligne:
    medicament = r.get("medicationCodeableConcept", {})
    posologie = (r.get("dosageInstruction") or [{}])[0]
    repetition = posologie.get("timing", {}).get("repeat", {})
    dose = ((posologie.get("doseAndRate") or [{}])[0]).get("doseQuantity", {})
    duree = repetition.get("boundsDuration", {}).get("value")
    quantite = r.get("dispenseRequest", {}).get("quantity", {})
    groupe = r.get("groupIdentifier") or {}
    return Ligne(
        id=r["id"],
        numero=groupe.get("value") if groupe.get("system") == systemes.ORDONNANCE else None,
        visite=id_de(r.get("encounter")),
        code=_code(medicament, systemes.CATALOGUE),
        produit=_texte(medicament) or "Produit",
        date=r.get("authoredOn", ""),
        moments=tuple(MOMENTS[m] for m in repetition.get("when", []) if m in MOMENTS),
        par_prise=dose.get("value"),
        jours=int(duree) if duree is not None else None,
        quantite=quantite.get("value"),
        unite=quantite.get("unit") or dose.get("unit"),
        etablissement=(r.get("dispenseRequest", {}).get("performer") or {}).get("reference"),
        prescripteur=(r.get("requester") or {}).get("reference"),
    )


def _acces(r: Ressource) -> Acces:
    agent = (r.get("agent") or [{}])[0]
    usage = (agent.get("purposeOfUse") or [{}])[0]
    source = r.get("source", {})
    observateur = (source.get("observer") or {}).get("reference")
    return Acces(
        date=r.get("recorded", ""),
        qui=(agent.get("who") or {}).get("reference"),
        etablissement=observateur if observateur and observateur.startswith("Organization/") else None,
        service=source.get("site"),
        motif=_code(usage, systemes.MOTIF_D_ACCES),
        raison=usage.get("text"),
    )


def _nom_de_personne(r: Ressource) -> str:
    nom = (r.get("name") or [{}])[0]
    return " ".join([*nom.get("given", [])[:1], nom.get("family", "").title()]).strip()


async def _noms(fhir: ClientFhir, references: set[str]) -> tuple[dict[str, str], dict[str, str]]:
    """Le nom de chaque Practitioner et Organization cité, et le rôle de chaque Practitioner."""
    par_type: dict[str, list[str]] = defaultdict(list)
    for ref in references:
        type_, _, id_ = ref.partition("/")
        if type_ in ("Practitioner", "Organization") and id_:
            par_type[type_].append(id_)
    noms: dict[str, str] = {}
    roles: dict[str, str] = {}
    lus = await asyncio.gather(*(fhir.chercher(t, {"_id": ",".join(sorted(ids))}) for t, ids in par_type.items()))
    for ressources in lus:
        for r in ressources:
            ref = f"{r['resourceType']}/{r['id']}"
            if r["resourceType"] == "Practitioner":
                noms[ref] = _nom_de_personne(r)
                role = _code((r.get("qualification") or [{}])[0].get("code"), systemes.ROLE)
                if role:
                    roles[ref] = role
            else:
                noms[ref] = (r.get("alias") or [None])[0] or r.get("name", "")
    return noms, roles


async def lire_dossier(fhir: ClientFhir, patient: Ressource) -> DossierDuCitoyen:
    """Tout ce que le carnet montre du dossier de `patient` : cas, visites, mesures, diagnostics,
    lignes d'ordonnance avec leur paiement et leur remise, allergies, et qui a ouvert le dossier."""
    ref = f"Patient/{patient['id']}"
    cas, visites, mesures, diagnostics, lignes, allergies, acces = await asyncio.gather(
        fhir.chercher("EpisodeOfCare", {"patient": ref}),
        fhir.chercher("Encounter", {"patient": ref}),
        fhir.chercher("Observation", {"patient": ref}),
        fhir.chercher("Condition", {"patient": ref}),
        fhir.chercher("MedicationRequest", {"patient": ref}),
        fhir.chercher("AllergyIntolerance", {"patient": ref}),
        fhir.chercher("AuditEvent", {"entity": ref}),
    )
    dossier = DossierDuCitoyen(
        patient=patient,
        cas=[_cas(r) for r in cas],
        visites=[_visite(r) for r in visites],
        mesures=[_mesure(r) for r in mesures],
        diagnostics=[_diagnostic(r) for r in diagnostics],
        lignes=[_ligne(r) for r in lignes],
        allergies=[_texte(r.get("code")) or "Allergie" for r in allergies],
        acces=[_acces(r) for r in acces],
    )

    # Payée : un encaissement de son ordonnance porte son identifiant. Remise : la somme de ses délivrances.
    numeros = sorted({ligne.numero for ligne in dossier.lignes if ligne.numero})
    ids = sorted(ligne.id for ligne in dossier.lignes)
    encaissements, delivrances = await asyncio.gather(
        fhir.chercher("Invoice", {"identifier": ",".join(f"{systemes.ORDONNANCE}|{n}" for n in numeros)})
        if numeros else asyncio.sleep(0, []),
        fhir.chercher("MedicationDispense", {"prescription": ",".join(f"MedicationRequest/{i}" for i in ids)})
        if ids else asyncio.sleep(0, []),
    )
    for facture in encaissements:
        if facture.get("status") in ("cancelled", "entered-in-error"):
            continue
        for poste in facture.get("lineItem", []):
            code = _code(poste.get("chargeItemCodeableConcept"), systemes.LIGNE)
            if code:
                dossier.payees.add(code)
    for delivrance in delivrances:
        if delivrance.get("status") not in (None, "completed"):
            continue
        for prescription in delivrance.get("authorizingPrescription", []):
            ligne = id_de(prescription)
            if ligne:
                quantite = delivrance.get("quantity", {}).get("value") or 0
                dossier.remis[ligne] = dossier.remis.get(ligne, 0) + quantite

    cites = {
        *(c.etablissement for c in dossier.cas),
        *(v.etablissement for v in dossier.visites),
        *(v.soignant for v in dossier.visites),
        *(ligne.etablissement for ligne in dossier.lignes),
        *(a.qui for a in dossier.acces),
        *(a.etablissement for a in dossier.acces),
    }
    dossier.noms, dossier.roles = await _noms(fhir, {c for c in cites if c})
    return dossier


def instant(texte: str) -> datetime | None:
    """Un `dateTime` FHIR en instant ; None quand il manque ou ne se lit pas."""
    try:
        return datetime.fromisoformat(texte.replace("Z", "+00:00"))
    except ValueError:
        return None
