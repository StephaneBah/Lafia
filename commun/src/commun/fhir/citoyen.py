"""Le dossier d'un patient tel que son carnet le lit : les ressources des contrats F3 et F4, traduites en choses.

Le service citoyen lit ici ce que soin, caisse et pharmacie écrivent (docs/specs/F3-v1-complete.md et
docs/specs/F4-dossier-approfondi.md, contrat FHIR) ; ses règles (`citoyen.regles`) en font les écrans du carnet. Rien n'est écrit ici, hors
de l'`AuditEvent` que chaque lecture laisse (`commun.fhir.dossier.tracer`).
"""

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from commun.fhir import systemes
from commun.fhir.client import ClientFhir, Ressource
from commun.fhir.documents import origine_de
from commun.fhir.dossier import id_de

MOMENTS = {"MORN": "matin", "NOON": "midi", "EVE": "soir", "NIGHT": "nuit"}

# Les codes LOINC que le carnet reconnaît.
TEMPERATURE = "8310-5"
SYSTOLIQUE = "8480-6"
DIASTOLIQUE = "8462-4"
GROUPE_SANGUIN = "882-1"

STATUT_CLINIQUE = "http://terminology.hl7.org/CodeSystem/condition-clinical"
LIENS_DE_PARENTE = {
    "MTH": "mere", "FTH": "pere", "SIB": "fratrie", "CHILD": "enfant", "GRMTH": "grand-parent", "GRFTH": "grand-parent", "GRPRN": "grand-parent",
}


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
    atc: str | None = None


@dataclass(frozen=True)
class Antecedent:
    type: str
    """`medical` ou `chirurgical`."""
    libelle: str
    depuis: str | None
    actif: bool
    date: str
    origine: str | None = None
    """D'où vient l'entrée (ADR 0007) : visite, declaration, report ; None avant F5."""


@dataclass(frozen=True)
class AntecedentFamilial:
    lien: str
    """`mere`, `pere`, `fratrie`, `enfant`, `grand-parent`, ou `parent` quand le lien n'est pas codé."""
    libelle: str
    origine: str | None = None


@dataclass(frozen=True)
class Allergie:
    libelle: str
    origine: str | None = None


@dataclass(frozen=True)
class TraitementAuLongCours:
    libelle: str
    posologie: str | None
    moments: tuple[str, ...]
    depuis: str | None
    actif: bool
    origine: str | None = None


@dataclass(frozen=True)
class Acces:
    date: str
    qui: str | None
    """La référence de qui a ouvert le dossier : `Practitioner/…`, `Organization/…` ou `Patient/…`."""
    etablissement: str | None
    service: str | None
    motif: str | None
    raison: str | None
    depot: str | None = None
    """Le Dépôt dont l'accès fait partie, par son étiquette `DEPOT` ; None hors du guichet de numérisation."""


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
    allergies_atc: list[str] = field(default_factory=list)
    """Le code ATC de chaque allergie codée : `M01A`, pour dire qu'une ligne a été arrêtée par elle."""
    allergies_lues: list[Allergie] = field(default_factory=list)
    """Chaque allergie, avec son origine."""
    antecedents: list[Antecedent] = field(default_factory=list)
    familiaux: list[AntecedentFamilial] = field(default_factory=list)
    traitements: list[TraitementAuLongCours] = field(default_factory=list)
    groupe_sanguin: str | None = None
    origine_du_groupe_sanguin: str | None = None
    acces: list[Acces] = field(default_factory=list)
    depots_avec_documents: set[str] = field(default_factory=set)
    """Les Dépôts qui ont ajouté au moins un Document au dossier, par leur étiquette `DEPOT`."""
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
        return Mesure(**base, systolique=valeurs.get(SYSTOLIQUE), diastolique=valeurs.get(DIASTOLIQUE))
    return Mesure(**base, resultat=_texte(r.get("valueCodeableConcept")))


def _diagnostic(r: Ressource) -> Diagnostic:
    code = r.get("code", {})
    return Diagnostic(
        visite=id_de(r.get("encounter")),
        libelle=_texte(code) or _code(code, systemes.DIAGNOSTIC) or "Diagnostic",
        confirme=_code(r.get("verificationStatus"), systemes.VERIFICATION) == "confirmed",
        gueri=_code(r.get("clinicalStatus"), STATUT_CLINIQUE) in ("resolved", "inactive"),
        note=((r.get("note") or [{}])[0]).get("text"),
    )


def _categories(r: Ressource, systeme: str) -> set[str]:
    return {c for categorie in r.get("category", []) if (c := _code(categorie, systeme))}


def est_un_antecedent(r: Ressource) -> bool:
    """Une Condition sans visite, ou de la liste des problèmes, est un antécédent : jamais le
    diagnostic d'une visite."""
    return "encounter" not in r or "problem-list-item" in _categories(r, systemes.CATEGORIE_DE_CONDITION)


def _antecedent(r: Ressource) -> Antecedent:
    types = _categories(r, systemes.TYPE_D_ANTECEDENT)
    return Antecedent(
        type="chirurgical" if "chirurgical" in types else "medical",
        libelle=_texte(r.get("code")) or "Antécédent",
        depuis=r.get("onsetString") or (r.get("onsetDateTime") or "")[:4] or None,
        actif=_code(r.get("clinicalStatus"), STATUT_CLINIQUE) not in ("resolved", "inactive", "remission"),
        date=r.get("recordedDate", ""),
        origine=origine_de(r),
    )


def _familial(r: Ressource) -> AntecedentFamilial:
    lien = _code(r.get("relationship"), systemes.LIEN_DE_PARENTE)
    return AntecedentFamilial(
        lien=LIENS_DE_PARENTE.get(lien or "", "parent"),
        libelle=_texte(((r.get("condition") or [{}])[0]).get("code")) or "Maladie",
        origine=origine_de(r),
    )


def _traitement(r: Ressource) -> TraitementAuLongCours:
    posologie = (r.get("dosage") or [{}])[0]
    repetition = posologie.get("timing", {}).get("repeat", {})
    return TraitementAuLongCours(
        libelle=_texte(r.get("medicationCodeableConcept")) or "Médicament",
        posologie=posologie.get("text"),
        moments=tuple(MOMENTS[m] for m in repetition.get("when", []) if m in MOMENTS),
        depuis=r.get("effectivePeriod", {}).get("start") or r.get("dateAsserted"),
        actif=r.get("status") in (None, "active", "intended"),
        origine=origine_de(r),
    )


def _groupe_sanguin(observations: list[Ressource]) -> tuple[str | None, str | None]:
    """Le dernier groupe sanguin relevé, et son origine : le plus récent l'emporte."""
    releves = [r for r in observations if _code(r.get("code"), systemes.LOINC) == GROUPE_SANGUIN]
    if not releves:
        return None, None
    dernier = max(releves, key=lambda r: r.get("effectiveDateTime") or r.get("issued") or "")
    return _texte(dernier.get("valueCodeableConcept")), origine_de(dernier)


def _etiquette(r: Ressource, systeme: str) -> str | None:
    return next((e.get("code") for e in r.get("meta", {}).get("tag", []) if e.get("system") == systeme), None)


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
        atc=_code(medicament, systemes.ATC),
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
        depot=_etiquette(r, systemes.DEPOT),
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
    lignes d'ordonnance avec leur paiement et leur remise, allergies, antécédents, traitements au long
    cours, groupe sanguin, et qui a ouvert le dossier."""
    ref = f"Patient/{patient['id']}"
    (
        cas, visites, observations, conditions, lignes, allergies, acces, familiaux, traitements, documents
    ) = await asyncio.gather(
        fhir.chercher("EpisodeOfCare", {"patient": ref}),
        fhir.chercher("Encounter", {"patient": ref}),
        fhir.chercher("Observation", {"patient": ref}),
        fhir.chercher("Condition", {"patient": ref}),
        fhir.chercher("MedicationRequest", {"patient": ref}),
        fhir.chercher("AllergyIntolerance", {"patient": ref}),
        fhir.chercher("AuditEvent", {"entity": ref}),
        fhir.chercher("FamilyMemberHistory", {"patient": ref}),
        fhir.chercher("MedicationStatement", {"subject": ref}),
        fhir.chercher("DocumentReference", {"subject": ref}),
    )
    groupe_sanguin, origine_du_groupe_sanguin = _groupe_sanguin(observations)
    dossier = DossierDuCitoyen(
        patient=patient,
        cas=[_cas(r) for r in cas],
        visites=[_visite(r) for r in visites],
        mesures=[_mesure(r) for r in observations if _code(r.get("code"), systemes.LOINC) != GROUPE_SANGUIN],
        diagnostics=[_diagnostic(r) for r in conditions if not est_un_antecedent(r)],
        lignes=[_ligne(r) for r in lignes],
        allergies=[_texte(r.get("code")) or "Allergie" for r in allergies],
        allergies_atc=[c for r in allergies if (c := _code(r.get("code"), systemes.ATC))],
        allergies_lues=[Allergie(libelle=_texte(r.get("code")) or "Allergie", origine=origine_de(r)) for r in allergies],
        antecedents=[_antecedent(r) for r in conditions if est_un_antecedent(r)],
        familiaux=[_familial(r) for r in familiaux if r.get("status") != "entered-in-error"],
        traitements=[_traitement(r) for r in traitements if r.get("status") != "entered-in-error"],
        groupe_sanguin=groupe_sanguin,
        origine_du_groupe_sanguin=origine_du_groupe_sanguin,
        acces=[_acces(r) for r in acces],
        depots_avec_documents={d for r in documents if (d := _etiquette(r, systemes.DEPOT))},
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
    for encaissement in encaissements:
        if encaissement.get("status") in ("cancelled", "entered-in-error"):
            continue
        for poste in encaissement.get("lineItem", []):
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
        *(ligne.prescripteur for ligne in dossier.lignes),
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
