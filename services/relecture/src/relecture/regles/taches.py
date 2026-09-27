"""Les Tâches de relecture (docs/specs/F6-relecture-et-extraction.md, ADR 0007, 0009).

Le triage : l'agent de relecture dit si le Document est utilisable, en corrige au besoin le type ou
l'année ; utilisable, il est lu par l'Extraction, dont les propositions entrent dans la Tâche, et la
Tâche passe au pool des soignants. La validation : un médecin ou un infirmier prend la Tâche, voit les
pages à côté des propositions, accepte, corrige ou rejette chacune ; les retenues entrent au dossier
avec l'origine `extraction` et leur Provenance, les rejetées restent dans la Tâche.

Personne ne voit ici qui est le patient : ni NPI, ni nom, ni lieu du dépôt ; seules les pages peuvent en
porter un. Le Document ne change jamais (ADR 0007) : une correction du triage vit dans la Tâche. Chaque
lecture d'une Tâche ou d'une page, et chaque écriture, laisse un AuditEvent au motif `relecture`.
"""

import base64
import logging
import re
import uuid
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ValidationError

from commun.extraction import MODELE_DE_DEMONSTRATION, DemandeDExtraction, Extraction, PageAExtraire
from commun.fhir import documents, dossier, relecture, systemes
from commun.fhir.client import ClientFhir, Ressource, TransactionRefusee, ecriture_si_inchangee
from commun.fhir.documents import Page
from commun.fhir.dossier import id_de, reference
from commun.fhir.relecture import Decision, Etape, PropositionVue, Verdict
from commun.jeton import Agent
from relecture.lecteur import Lecteur
from relecture.regles import acces
from relecture.regles.attribution import attribuer

SERVICE = "relecture"
MOTIF = "relecture"
LIBRES_A_LA_FOIS = 5
"""Combien de Tâches de validation libres un soignant voit à la fois, en plus de celles qu'il a prises."""
ANNEE = re.compile(r"^(19|20)\d{2}$")

journal = logging.getLogger(SERVICE)


class TacheIntrouvable(Exception):
    """Aucune Tâche de relecture sous cet identifiant."""


class TacheDUnAutre(Exception):
    """La Tâche n'est pas celle de ce relecteur, ou pas de son étape."""


class RoleRefuse(Exception):
    """Le rôle ne fait pas cette action : l'agent de relecture ne valide pas, le soignant ne trie pas."""


class TacheDejaFaite(Exception):
    """La Tâche n'est plus à cette étape : triée, validée, ou prise par un autre au même instant."""


class PageIntrouvable(Exception):
    """Aucune page à ce rang."""


class SaisieRefusee(ValueError):
    """Un type, une année, une proposition ou une valeur que la relecture n'admet pas."""


class DocumentALire(BaseModel):
    """Ce que le relecteur voit du Document : son type, son année, ses pages. Jamais de qui il est."""

    type: str
    libelle: str
    annee: str | None
    pages: int
    formats: list[str]
    """Le format de chaque page, dans l'ordre : image/jpeg, image/png ou application/pdf."""
    lisibilite: str | None


class TacheResumee(BaseModel):
    id: str
    etape: Etape
    statut: Literal["a-faire", "en-cours", "terminee"]
    document: DocumentALire
    echeance: str | None
    verdict: str | None


class ModeleLu(BaseModel):
    nom: str
    version: str
    demonstration: bool
    """Vrai pour l'Extraction de démonstration : chaque écran le dit."""


class TacheVue(TacheResumee):
    propositions: list[PropositionVue] | None = None
    modele: ModeleLu | None = None
    texte: str | None = None


class DecisionRecue(BaseModel):
    id: str
    decision: Decision
    valeur: str | None = None


class EntreeEcrite(BaseModel):
    type: str
    id: str


class Validation(BaseModel):
    id: str
    entrees: list[EntreeEcrite]
    rejetees: int


# Lire une Tâche, et qui y a droit.


async def _tache(fhir: ClientFhir, tache_id: str) -> Ressource:
    tache = await fhir.lire("Task", tache_id)
    codes = [c.get("system") for c in (tache or {}).get("code", {}).get("coding", [])]
    if not tache or systemes.RELECTURE not in codes:
        raise TacheIntrouvable()
    return tache


def _a_moi(tache: Ressource, agent: Agent) -> bool:
    return id_de(tache.get("owner")) == agent.sub


def _libre(tache: Ressource) -> bool:
    return tache.get("status") == "ready" and not tache.get("owner")


async def _ecrire(fhir: ClientFhir, suivante: Ressource, lue: Ressource) -> None:
    try:
        await fhir.transaction([ecriture_si_inchangee(suivante, lue)])
    except TransactionRefusee as erreur:
        raise TacheDejaFaite() from erreur


async def _tache_de(fhir: ClientFhir, agent: Agent, tache_id: str, *, prendre: bool = False) -> Ressource:
    """La Tâche, si cet agent y a droit : l'agent de relecture, ses Tâches de triage ; le soignant, les
    Tâches de validation qu'il a prises, et une libre quand il l'ouvre (`prendre`), qui devient la sienne."""
    tache = await _tache(fhir, tache_id)
    etape = relecture.etape_de(tache)
    if acces.fait_le_triage(agent):
        if etape != "triage" or not _a_moi(tache, agent):
            raise TacheDUnAutre()
        return tache
    if etape != "validation":
        raise TacheDUnAutre()
    if _a_moi(tache, agent):
        return tache
    if prendre and _libre(tache):
        await _ecrire(fhir, relecture.prise(tache, agent.sub), tache)
        journal.info("tâche %s prise par le soignant %s", tache_id, agent.sub)
        return await _tache(fhir, tache_id)
    raise TacheDUnAutre()


async def _tracer(fhir: ClientFhir, agent: Agent, tache: Ressource, action: dossier.Action) -> None:
    patient = relecture.patient_de(tache)
    scan = relecture.document_de(tache)
    if not patient:
        return
    await dossier.tracer(
        fhir,
        patient=patient,
        qui=reference("Practitioner", agent.sub),
        service=SERVICE,
        action=action,
        motif=MOTIF,
        etablissement=agent.etablissement,
        ressource=reference("DocumentReference", scan) if scan else None,
    )


# Ce que le relecteur voit.


async def _document(fhir: ClientFhir, tache: Ressource) -> Ressource:
    scan = relecture.document_de(tache)
    document = await fhir.lire("DocumentReference", scan) if scan else None
    if not document:
        raise TacheIntrouvable()
    return document


def _document_a_lire(document: Ressource, tache: Ressource) -> DocumentALire:
    vu = documents.document_vu(document)
    type_corrige, annee_corrigee = relecture.corrections_de(tache)
    type_ = type_corrige or vu.type
    return DocumentALire(
        type=type_,
        libelle=documents.TYPES_DE_DOCUMENT.get(type_, vu.libelle_du_type),
        annee=annee_corrigee or vu.annee,
        pages=vu.pages,
        formats=documents.formats_des_pages(document),
        lisibilite=vu.lisibilite,
    )


def _statut(tache: Ressource) -> Literal["a-faire", "en-cours", "terminee"]:
    return {"ready": "a-faire", "in-progress": "en-cours"}.get(tache.get("status", ""), "terminee")  # type: ignore[return-value]


def _resumee(tache: Ressource, document: Ressource) -> TacheResumee:
    return TacheResumee(
        id=tache["id"],
        etape=relecture.etape_de(tache),
        statut=_statut(tache),
        document=_document_a_lire(document, tache),
        echeance=relecture.echeance_de(tache),
        verdict=relecture.verdict_de(tache),
    )


async def _texte_lu(fhir: ClientFhir, tache: Ressource) -> str | None:
    texte_id = relecture.texte_de(tache)
    texte = await fhir.lire("DocumentReference", texte_id) if texte_id else None
    url = next(iter((texte or {}).get("content", [])), {}).get("attachment", {}).get("url", "")
    binary = await fhir.lire("Binary", url.rsplit("/", 1)[-1]) if url else None
    return base64.b64decode(binary.get("data", "")).decode() if binary else None


async def mes_taches(fhir: ClientFhir, agent: Agent, jour: date) -> list[TacheResumee]:
    """Les Tâches de l'agent. L'agent de relecture : celles de sa semaine, complétées jusqu'à son quota.
    Le soignant : les Tâches de validation qu'il a prises, et quelques libres, les plus anciennes d'abord."""
    if acces.fait_le_triage(agent):
        await attribuer(fhir, agent, jour)
        taches = await relecture.taches_de(fhir, agent.sub, relecture.semaine(jour))
    else:
        validation = f"{systemes.RELECTURE}|validation"
        prises = await fhir.chercher("Task", {"code": validation, "owner": f"Practitioner/{agent.sub}", "status": "in-progress"})
        libres = [t for t in await fhir.chercher("Task", {"code": validation, "status": "ready"}) if _libre(t)]
        taches = prises + sorted(libres, key=lambda t: t.get("authoredOn", ""))[:LIBRES_A_LA_FOIS]
    resumees = []
    for tache in taches:
        document = await fhir.lire("DocumentReference", relecture.document_de(tache) or "")
        if document:
            resumees.append(_resumee(tache, document))
    ordre = {"en-cours": 0, "a-faire": 1, "terminee": 2}
    return sorted(resumees, key=lambda t: (ordre[t.statut], t.document.annee or "9999"))


async def lire_tache(fhir: ClientFhir, agent: Agent, tache_id: str) -> TacheVue:
    """Une Tâche : le Document sans qui il est, et à la validation, les propositions, le modèle, le texte lu.
    Un soignant qui ouvre une Tâche de validation libre la prend."""
    tache = await _tache_de(fhir, agent, tache_id, prendre=True)
    document = await _document(fhir, tache)
    vue = TacheVue(**_resumee(tache, document).model_dump())
    modele = relecture.modele_de(tache)
    if modele:
        vue.modele = ModeleLu(nom=modele.nom, version=modele.version, demonstration=modele == MODELE_DE_DEMONSTRATION)
        vue.propositions = relecture.propositions_de(tache)
        vue.texte = await _texte_lu(fhir, tache)
    await _tracer(fhir, agent, tache, "read")
    return vue


async def lire_page(fhir: ClientFhir, agent: Agent, tache_id: str, rang: int) -> Page:
    """La page `rang` (à partir de 1) du Document d'une Tâche, pour qui la tient."""
    tache = await _tache_de(fhir, agent, tache_id)
    lue = await documents.page(fhir, await _document(fhir, tache), rang)
    if not lue:
        raise PageIntrouvable()
    await _tracer(fhir, agent, tache, "read")
    return lue


# Le triage.


def _verifier_corrections(type_: str | None, annee: str | None, jour: date) -> None:
    if type_ is not None and type_ not in documents.TYPES_DE_DOCUMENT:
        raise SaisieRefusee("type de document inconnu")
    if annee is not None and not (ANNEE.match(annee) and int(annee) <= jour.year):
        raise SaisieRefusee("année sur quatre chiffres, passée")


def _texte_des_corrections(type_: str | None, annee: str | None) -> str:
    morceaux = []
    if type_:
        morceaux.append(f"type corrigé : {documents.TYPES_DE_DOCUMENT[type_]}")
    if annee:
        morceaux.append(f"année corrigée : {annee}")
    return " ; ".join(morceaux)


def dater(extraction: Extraction, annee: str | None) -> Extraction:
    """Une mesure ou un traitement lus sans date prennent l'année du papier : c'est d'elle qu'ils datent."""
    if not annee or not ANNEE.match(annee):
        return extraction
    datee = extraction.model_copy(deep=True)
    for proposition in datee.propositions:
        ressource = proposition.ressource
        if ressource.get("resourceType") in ("Observation", "MedicationStatement") and not any(
            cle.startswith("effective") for cle in ressource
        ):
            ressource["effectiveDateTime"] = annee
    return datee


async def _extraire(fhir: ClientFhir, lecteur: Lecteur, document: Ressource, type_: str) -> Extraction:
    pages = []
    for rang in range(1, len(document.get("content", [])) + 1):
        page = await documents.page(fhir, document, rang)
        if page:
            pages.append(PageAExtraire(format=page.format, octets=base64.b64encode(page.octets).decode()))  # type: ignore[arg-type]
    try:
        demande = DemandeDExtraction(document_id=document["id"], type_de_document=type_, pages=pages)
    except ValidationError as erreur:
        raise SaisieRefusee("pages illisibles pour l'Extraction") from erreur
    return await lecteur.extraire(demande)


async def trier(
    fhir: ClientFhir,
    lecteur: Lecteur,
    agent: Agent,
    tache_id: str,
    *,
    verdict: Verdict,
    type_: str | None,
    annee: str | None,
    jour: date,
) -> TacheResumee:
    """Le verdict de l'agent de relecture. Utilisable, le Document est lu par l'Extraction : son texte
    devient un Document dérivé, ses propositions entrent dans la Tâche, qui passe au pool des soignants.
    Tout autre verdict clôt la Tâche. Une correction du type ou de l'année reste dans la Tâche."""
    if not acces.fait_le_triage(agent):
        raise RoleRefuse()
    tache = await _tache_de(fhir, agent, tache_id)
    if tache.get("status") != "ready":
        raise TacheDejaFaite()
    type_ = type_ or None
    annee = (annee or "").strip() or None
    _verifier_corrections(type_, annee, jour)
    document = await _document(fhir, tache)
    suivante = relecture.avec_corrections(tache, type_=type_, annee=annee) if (type_ or annee) else tache
    suivante = relecture.apres_triage(suivante, verdict, agent.sub)
    corrections = _texte_des_corrections(type_, annee)
    if corrections:
        suivante["note"][-1]["text"] += f" ; {corrections}"
        suivante["businessStatus"]["text"] += f" ; {corrections}"
    if verdict == "utilisable":
        a_lire = _document_a_lire(document, suivante)
        extraction = dater(await _extraire(fhir, lecteur, document, a_lire.type), a_lire.annee)
        patient = relecture.patient_de(tache) or ""
        await fhir.mettre_a_jour(relecture.device(extraction.modele))
        binary = await fhir.creer(relecture.binary_de_texte(extraction.texte, patient))
        texte = await fhir.creer(
            relecture.document_de_texte(
                scan=document["id"], patient=patient, texte=extraction.texte, modele=extraction.modele, binary=binary["id"]
            )
        )
        suivante = relecture.avec_extraction(suivante, extraction, texte["id"])
        journal.info(
            "tâche %s : document %s lu par %s:%s, %d propositions",
            tache_id,
            document["id"],
            extraction.modele.nom,
            extraction.modele.version,
            len(suivante.get("contained", [])),
        )
    await _ecrire(fhir, suivante, tache)
    await _tracer(fhir, agent, tache, "update")
    journal.info("tâche %s triée par l'agent %s : %s", tache_id, agent.sub, verdict)
    return _resumee(suivante, document)


# La validation.

VERIFICATION_D_ALLERGIE = "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification"


def verifiee_par(entree: Ressource, agent: Agent) -> Ressource:
    """Un antécédent ou une allergie qu'un médecin accepte est confirmé ; accepté par un infirmier, il
    reste à confirmer (provisoire, ou non confirmée), comme ses diagnostics de visite."""
    medecin = acces.confirme_un_diagnostic(agent)
    if entree["resourceType"] == "Condition":
        code, libelle = ("confirmed", "Confirmé") if medecin else ("provisional", "Provisoire")
        entree["verificationStatus"] = {"coding": [{"system": systemes.VERIFICATION, "code": code, "display": libelle}], "text": libelle}
    elif entree["resourceType"] == "AllergyIntolerance":
        code, libelle = ("confirmed", "Confirmée") if medecin else ("unconfirmed", "Non confirmée")
        entree["verificationStatus"] = {"coding": [{"system": VERIFICATION_D_ALLERGIE, "code": code, "display": libelle}], "text": libelle}
    return entree


def _decisions(tache: Ressource, recues: list[DecisionRecue]) -> dict[str, DecisionRecue]:
    """Les décisions du soignant, une par proposition connue ; une proposition qu'il ne cite pas est rejetée."""
    connues = {r.get("id") for r in tache.get("contained", [])}
    decisions: dict[str, DecisionRecue] = {}
    for recue in recues:
        if recue.id not in connues:
            raise SaisieRefusee(f"proposition inconnue : {recue.id}")
        if recue.id in decisions:
            raise SaisieRefusee(f"proposition décidée deux fois : {recue.id}")
        if recue.decision == "corriger" and not (recue.valeur or "").strip():
            raise SaisieRefusee("une correction porte sa valeur")
        decisions[recue.id] = recue
    return decisions


def _type_et_id(ref: str) -> tuple[str | None, str | None]:
    """`Condition/123`, avec ou sans `/_history/1` derrière : ("Condition", "123")."""
    morceaux = ref.split("/_history/")[0].split("/")
    return (morceaux[-2], morceaux[-1]) if len(morceaux) >= 2 else (None, None)


async def valider(fhir: ClientFhir, agent: Agent, tache_id: str, recues: list[DecisionRecue]) -> Validation:
    """La validation du soignant qui tient la Tâche : chaque proposition acceptée ou corrigée entre au
    dossier (origine `extraction`, et son Provenance : le Document lu, le soignant, le modèle) ; la
    Tâche est close, les rejetées y restent. Tout est écrit en une transaction, ou rien."""
    if not acces.valide(agent):
        raise RoleRefuse()
    tache = await _tache_de(fhir, agent, tache_id)
    modele = relecture.modele_de(tache)
    if tache.get("status") != "in-progress" or modele is None:
        raise TacheDejaFaite()
    decisions = _decisions(tache, recues)
    patient = relecture.patient_de(tache) or ""
    scan = relecture.document_de(tache) or ""
    ecritures: list[dict[str, Any]] = []
    cibles: list[dict[str, str]] = []
    for proposition, recue in decisions.items():
        if recue.decision == "rejeter":
            continue
        brouillon = relecture.brouillon_de(tache, proposition) or {}
        try:
            entree = relecture.entree_validee(
                brouillon,
                patient=patient,
                soignant=agent.sub,
                valeur_corrigee=recue.valeur.strip() if recue.decision == "corriger" and recue.valeur else None,
            )
        except ValueError as erreur:
            raise SaisieRefusee("valeur corrigée illisible : un nombre est attendu") from erreur
        cible = {"reference": f"urn:uuid:{uuid.uuid4()}"}
        cibles.append(cible)
        ecritures.append(
            {"fullUrl": cible["reference"], "resource": verifiee_par(entree, agent), "request": {"method": "POST", "url": entree["resourceType"]}}
        )
        ecritures.append(
            {
                "resource": relecture.provenance_d_extraction(cible=cible, scan=scan, soignant=agent.sub, modele=modele),
                "request": {"method": "POST", "url": "Provenance"},
            }
        )
    suivante = relecture.apres_validation(tache, {k: v.decision for k, v in decisions.items()}, agent.sub, cibles)
    ecritures.append(ecriture_si_inchangee(suivante, tache))
    try:
        await fhir.transaction(ecritures)
    except TransactionRefusee as erreur:
        journal.warning("validation de la tâche %s refusée par le noyau : %s", tache_id, erreur)
        raise TacheDejaFaite() from erreur
    await _tracer(fhir, agent, tache, "create")
    # Le noyau a remplacé chaque `urn:uuid:` par l'identifiant de l'entrée écrite.
    relue = await _tache(fhir, tache_id)
    entrees = [
        _type_et_id(o.get("valueReference", {}).get("reference", ""))
        for o in relue.get("output", [])
        if o.get("type", {}).get("text") == "Entrée validée"
    ]
    retenues = len(cibles)
    journal.info("tâche %s validée par le soignant %s : %d retenues", tache_id, agent.sub, retenues)
    return Validation(
        id=tache_id,
        entrees=[EntreeEcrite(type=type_, id=id_) for type_, id_ in entrees if type_ and id_],
        rejetees=len(tache.get("contained", [])) - retenues,
    )
