"""Les Tâches de relecture (docs/specs/F6-relecture-et-extraction.md, ADR 0007, 0009, 0010).

La Relecture : l'agent de relecture ouvre une Tâche de sa semaine ; à la première ouverture, le Document
est lu par l'Extraction, dont le brouillon de Transcription, le texte lu et les propositions entrent dans
la Tâche. Il corrige le brouillon (enregistré dans la Tâche, sous `If-Match` sur sa version), coche chaque
volet vérifié contre ses pages, puis confirme le tout avec le résumé de ses changements : une version de
la Transcription est écrite (préliminaire), avec son Provenance, et un Contrôle naît au pool, pour un autre
agent de relecture. `PART_CONTROLEE` (1 par défaut) dit quelle part des confirmations passe au Contrôle :
les autres sont relues d'emblée.

Le Contrôle : le contrôleur, jamais l'auteur, lit la Transcription contre les pages et l'accepte (une
version finale, son Provenance ; les propositions de l'Extraction passent alors aux soignants) ou la
renvoie à son relecteur avec une note, le brouillon gardé.

Un Document inutilisable (pas médical, déjà numérisé) est clos sans Transcription ; rien ne rappelle le
citoyen. La validation : un médecin ou un infirmier prend une Tâche de validation, accepte, corrige ou
rejette chaque proposition ; les retenues entrent au dossier avec l'origine `extraction`.

Personne ne voit ici qui est le patient : ni NPI, ni nom, ni lieu du dépôt ; seules les pages peuvent en
porter un. Le Document ne change jamais (ADR 0007). Chaque lecture d'une Tâche ou d'une page, et chaque
écriture, laisse un AuditEvent au motif `relecture`.
"""

import base64
import logging
import os
import random
import re
import uuid
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ValidationError

from commun import transcription as format_de_transcription
from commun.extraction import MODELE_DE_DEMONSTRATION, DemandeDExtraction, Extraction, PageAExtraire
from commun.fhir import documents, dossier, relecture, systemes
from commun.fhir.client import ClientFhir, Ressource, TransactionRefusee, ecriture, ecriture_si_inchangee
from commun.fhir.documents import Page
from commun.fhir.dossier import id_de, reference
from commun.fhir.relecture import Decision, DecisionDeControle, Etape, PropositionVue, Raison
from commun.jeton import Agent
from relecture.lecteur import Lecteur
from relecture.regles import acces
from relecture.regles.attribution import attribuer

SERVICE = "relecture"
MOTIF = "relecture"
LIBRES_A_LA_FOIS = 5
"""Combien de Tâches de validation libres un soignant voit à la fois, en plus de celles qu'il a prises."""
TAILLE_MAXIMALE = 200 * 1024
"""Un brouillon de Transcription tient en 200 Ko : un carnet entier en fait quelques dizaines."""
HISTORIQUE = 50
"""Combien de Relectures et de Contrôles passés le suivi rend, les plus récents d'abord."""
ANNEE = re.compile(r"^(19|20)\d{2}$")

journal = logging.getLogger(SERVICE)


def part_controlee() -> float:
    """La part des Transcriptions confirmées qui passent au Contrôle : `PART_CONTROLEE`, entre 0 et 1, ou 1."""
    try:
        part = float(os.environ.get("PART_CONTROLEE", "") or 1)
    except ValueError:
        return 1.0
    return min(1.0, max(0.0, part))


class TacheIntrouvable(Exception):
    """Aucune Tâche de relecture sous cet identifiant."""


class TacheDUnAutre(Exception):
    """La Tâche n'est pas celle de cet agent, ou pas d'une étape qu'il fait sur elle."""


class RoleRefuse(Exception):
    """Le rôle ne fait pas cette action : l'agent de relecture ne valide pas, le soignant ne relit pas."""


class TacheDejaFaite(Exception):
    """La Tâche n'est plus à cette étape : confirmée, contrôlée, close, ou changée par un autre au même instant."""


class VersionAbsente(Exception):
    """Un enregistrement sans `If-Match` : il écraserait sans le savoir ce qu'un autre onglet a enregistré."""


class VersionPerimee(Exception):
    """`If-Match` ne porte plus la version de la Tâche : quelqu'un l'a enregistrée depuis."""


class PageIntrouvable(Exception):
    """Aucune page à ce rang."""


class SaisieRefusee(ValueError):
    """Une saisie que la relecture n'admet pas."""


class TranscriptionRefusee(Exception):
    """Une confirmation refusée : ce que le Markdown ne suit pas de l'ADR 0010, les volets non cochés."""

    def __init__(self, erreurs: list[str], volets_non_verifies: list[int]) -> None:
        super().__init__("transcription à reprendre")
        self.erreurs = erreurs
        self.volets_non_verifies = volets_non_verifies


Statut = Literal["a-faire", "en-cours", "terminee"]


class DocumentALire(BaseModel):
    """Ce que le relecteur voit du Document : son type, son année, ses pages. Jamais de qui il est."""

    type: str
    libelle: str
    annee: str | None
    pages: int
    formats: list[str]
    """Le format de chaque page, dans l'ordre : image/jpeg, image/png ou application/pdf."""


class TacheResumee(BaseModel):
    id: str
    etape: Etape
    statut: Statut
    document: DocumentALire
    echeance: str | None
    renvoyee: bool
    """Une Relecture que le Contrôle a renvoyée à son relecteur, et qu'il n'a pas encore confirmée de nouveau."""


class ModeleLu(BaseModel):
    nom: str
    version: str
    demonstration: bool
    """Vrai pour l'Extraction de démonstration : chaque écran le dit."""


class VoletVu(BaseModel):
    rang: int
    titre: str
    type: str
    date: str | None
    etablissement: str | None
    pages: list[int]


class NoteVue(BaseModel):
    date: str | None
    texte: str


class TacheVue(TacheResumee):
    version: str
    """La version de la Tâche, à renvoyer en `If-Match` avec un brouillon (aussi dans l'en-tête ETag)."""
    markdown: str | None = None
    """Le brouillon à la Relecture ; la Transcription confirmée au Contrôle ; la relue à la validation."""
    volets: list[VoletVu] = []
    erreurs: list[str] = []
    """Ce que le Markdown ne suit pas de l'ADR 0010 : une confirmation le refuse."""
    texte: str | None = None
    modele: ModeleLu | None = None
    notes_de_controle: list[NoteVue] = []
    resume: str | None = None
    propositions: list[PropositionVue] | None = None


class Enregistrement(BaseModel):
    id: str
    version: str


class Confirmation(BaseModel):
    id: str
    statut: Statut
    transcription: str | None
    """La version écrite de la Transcription."""
    relue: bool
    """Vrai quand aucun Contrôle ne suit : la version est déjà finale."""
    controle: str | None
    """La Tâche de Contrôle née de la confirmation, au pool des Contrôles."""


class Controle(BaseModel):
    id: str
    decision: DecisionDeControle
    transcription: str | None
    """La version finale, quand le Contrôle l'accepte."""
    validation: str | None
    """La Tâche de validation des propositions, quand l'Extraction en a fait."""


class Evenement(BaseModel):
    id: str
    etape: Etape
    date: str
    issue: str | None


class Semaine(BaseModel):
    a_relire: int
    confirmees: int
    renvoyees: int
    controlees: int


class Suivi(BaseModel):
    semaine: Semaine
    historique: list[Evenement]


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
    if not tache or relecture.etape_de(tache) is None:
        raise TacheIntrouvable()
    return tache


def _a_moi(tache: Ressource, agent: Agent) -> bool:
    return relecture.relecteur_de(tache) == agent.sub


def _libre(tache: Ressource) -> bool:
    return tache.get("status") == "ready" and not tache.get("owner")


def _version(tache: Ressource) -> str:
    return str(tache.get("meta", {}).get("versionId", "1"))


async def _ecrire(fhir: ClientFhir, suivante: Ressource, lue: Ressource) -> None:
    try:
        await fhir.transaction([ecriture_si_inchangee(suivante, lue)])
    except TransactionRefusee as erreur:
        raise TacheDejaFaite() from erreur


async def _tache_de(fhir: ClientFhir, agent: Agent, tache_id: str, *, prendre: bool = False) -> Ressource:
    """La Tâche, si cet agent y a droit : l'agent de relecture, ses Relectures et ses Contrôles (jamais le
    Contrôle de sa propre relecture) ; le soignant, les Tâches de validation qu'il a prises, et une libre
    quand il l'ouvre (`prendre`), qui devient la sienne."""
    tache = await _tache(fhir, tache_id)
    etape = relecture.etape_de(tache)
    if acces.relit(agent):
        if etape not in ("relecture", "controle") or not _a_moi(tache, agent):
            raise TacheDUnAutre()
        if etape == "controle" and relecture.auteur_de(tache) == agent.sub:
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


async def _tache_a_relire(fhir: ClientFhir, agent: Agent, tache_id: str) -> Ressource:
    """Une Relecture de cet agent, encore ouverte : ce que l'enregistrement, la confirmation et la
    clôture exigent."""
    if not acces.relit(agent):
        raise RoleRefuse()
    tache = await _tache_de(fhir, agent, tache_id)
    if relecture.etape_de(tache) != "relecture":
        raise TacheDUnAutre()
    if not relecture.est_ouverte(tache):
        raise TacheDejaFaite()
    return tache


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


# Ce que l'agent voit.


async def _document(fhir: ClientFhir, tache: Ressource) -> Ressource:
    scan = relecture.document_de(tache)
    document = await fhir.lire("DocumentReference", scan) if scan else None
    if not document:
        raise TacheIntrouvable()
    return document


def _document_a_lire(document: Ressource) -> DocumentALire:
    vu = documents.document_vu(document)
    return DocumentALire(type=vu.type, libelle=vu.libelle, annee=vu.annee, pages=vu.pages, formats=vu.formats)


def _statut(tache: Ressource) -> Statut:
    return {"ready": "a-faire", "in-progress": "en-cours"}.get(tache.get("status", ""), "terminee")  # type: ignore[return-value]


def _resumee(tache: Ressource, document: Ressource) -> TacheResumee:
    return TacheResumee(
        id=tache["id"],
        etape=relecture.etape_de(tache) or "relecture",
        statut=_statut(tache),
        document=_document_a_lire(document),
        echeance=relecture.echeance_de(tache),
        renvoyee=relecture.etape_de(tache) == "relecture" and relecture.issue_de(tache) == "renvoyee",
    )


async def mes_taches(fhir: ClientFhir, agent: Agent, jour: date) -> list[TacheResumee]:
    """Les Tâches de l'agent. L'agent de relecture : sa semaine, complétée jusqu'à son quota, et ce qu'il
    tient encore ouvert d'avant. Le soignant : les Tâches de validation qu'il a prises, et quelques libres,
    les plus anciennes d'abord."""
    if acces.relit(agent):
        await attribuer(fhir, agent, jour)
        par_id = {
            t["id"]: t
            for t in [
                *await relecture.taches_de(fhir, agent.sub, relecture.semaine(jour)),
                *await relecture.taches_ouvertes_de(fhir, agent.sub),
            ]
        }
        taches = [t for t in par_id.values() if relecture.etape_de(t) in ("relecture", "controle")]
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
    return sorted(resumees, key=lambda t: (ordre[t.statut], t.document.annee or "9999", t.id))


async def _markdown_de_la_version(fhir: ClientFhir, version_id: str | None) -> str | None:
    version = await fhir.lire("DocumentReference", version_id) if version_id else None
    return await relecture.markdown_de(fhir, version) if version else None


async def _vue(fhir: ClientFhir, tache: Ressource, document: Ressource) -> TacheVue:
    etape = relecture.etape_de(tache)
    vue = TacheVue(**_resumee(tache, document).model_dump(), version=_version(tache))
    # D'où viennent le texte, le modèle et les notes : la Relecture elle-même, ou celle qu'un Contrôle vise.
    source = tache
    if etape == "controle":
        source = await fhir.lire("Task", relecture.relecture_de(tache) or "") or tache
    if etape == "relecture":
        vue.markdown = relecture.brouillon_de(tache)
    else:
        vue.markdown = await _markdown_de_la_version(fhir, relecture.transcription_de(tache))
    if vue.markdown is not None:
        lue = format_de_transcription.lire(vue.markdown, vue.document.pages)
        vue.volets = [
            VoletVu(rang=v.rang, titre=v.titre, type=v.type, date=v.date, etablissement=v.etablissement, pages=list(v.pages))
            for v in lue.volets
        ]
        vue.erreurs = list(lue.erreurs)
    vue.texte = relecture.texte_lu_de(source)
    modele = relecture.modele_de(source)
    if modele:
        vue.modele = ModeleLu(nom=modele.nom, version=modele.version, demonstration=modele == MODELE_DE_DEMONSTRATION)
    vue.notes_de_controle = [NoteVue(date=n.date, texte=n.texte) for n in relecture.notes_de_controle(source)]
    vue.resume = relecture.resume_de(tache)
    if etape == "validation":
        vue.propositions = relecture.propositions_de(tache)
    return vue


async def lire_tache(fhir: ClientFhir, lecteur: Lecteur, agent: Agent, tache_id: str) -> TacheVue:
    """Une Tâche : le Document sans qui il est, la Transcription et ses volets, le texte lu, le modèle, les
    notes du Contrôle. Une Relecture ouverte pour la première fois est d'abord lue par l'Extraction. Un
    soignant qui ouvre une Tâche de validation libre la prend."""
    tache = await _tache_de(fhir, agent, tache_id, prendre=True)
    document = await _document(fhir, tache)
    if relecture.etape_de(tache) == "relecture" and relecture.est_ouverte(tache) and relecture.brouillon_de(tache) is None:
        tache = await _ouvrir(fhir, lecteur, tache, document)
    vue = await _vue(fhir, tache, document)
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


# L'Extraction, à la première ouverture.


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


async def _ouvrir(fhir: ClientFhir, lecteur: Lecteur, tache: Ressource, document: Ressource) -> Ressource:
    """La Relecture reçoit son Extraction : brouillon, texte lu, propositions, modèle. Elle passe en cours."""
    vu = documents.document_vu(document)
    extraction = dater(await _extraire(fhir, lecteur, document, vu.type), vu.annee)
    await fhir.mettre_a_jour(relecture.device(extraction.modele))
    suivante = relecture.avec_extraction(tache, extraction)
    await _ecrire(fhir, suivante, tache)
    journal.info(
        "tâche %s : document %s lu par %s:%s, %d propositions",
        tache["id"],
        document["id"],
        extraction.modele.nom,
        extraction.modele.version,
        len(suivante.get("contained", [])),
    )
    return await _tache(fhir, tache["id"])


# La Relecture : enregistrer, confirmer, clore.


def _version_attendue(si_version: str) -> str:
    """`W/"3"`, `"3"` ou `3` : la version 3."""
    valeur = si_version.strip()
    if valeur.startswith("W/"):
        valeur = valeur[2:]
    return valeur.strip().strip('"')


async def enregistrer(fhir: ClientFhir, agent: Agent, tache_id: str, markdown: str, si_version: str | None) -> Enregistrement:
    """Le brouillon corrigé du relecteur, enregistré dans la Tâche à la place du précédent, si la Tâche
    est encore à la version qu'il a lue. Ce n'est pas une version de la Transcription."""
    if not acces.relit(agent):
        raise RoleRefuse()
    if len(markdown.encode()) > TAILLE_MAXIMALE:
        raise SaisieRefusee("transcription de plus de 200 Ko")
    tache = await _tache_a_relire(fhir, agent, tache_id)
    if si_version is None:
        raise VersionAbsente()
    if _version_attendue(si_version) != _version(tache):
        raise VersionPerimee()
    if relecture.brouillon_de(tache) is None:
        raise SaisieRefusee("tâche à ouvrir avant d'en enregistrer la transcription")
    await _ecrire(fhir, relecture.avec_brouillon(tache, markdown), tache)
    await _tracer(fhir, agent, tache, "update")
    ecrite = await _tache(fhir, tache_id)
    return Enregistrement(id=tache_id, version=_version(ecrite))


def _a_reprendre(markdown: str, pages: int, volets_verifies: list[int], resume: str) -> TranscriptionRefusee | None:
    """Ce qui empêche de confirmer : le Markdown hors de l'ADR 0010, un volet non coché, pas de résumé."""
    lue = format_de_transcription.lire(markdown, pages)
    erreurs = list(lue.erreurs)
    if not lue.volets:
        erreurs.append("aucun volet : une Transcription en compte au moins un")
    if not resume:
        erreurs.append("résumé des changements manquant")
    verifies = set(volets_verifies)
    manquants = [v.rang for v in lue.volets if v.rang not in verifies]
    return TranscriptionRefusee(erreurs, manquants) if erreurs or manquants else None


def _nouvelle(cible: dict[str, str], ressource: Ressource) -> dict[str, Any]:
    return {"fullUrl": cible["reference"], "resource": ressource, "request": {"method": "POST", "url": ressource["resourceType"]}}


def _creee(ressource: Ressource) -> dict[str, Any]:
    return {"resource": ressource, "request": {"method": "POST", "url": ressource["resourceType"]}}


async def confirmer(
    fhir: ClientFhir, agent: Agent, tache_id: str, *, volets_verifies: list[int], resume: str
) -> Confirmation:
    """La double confirmation du relecteur : chaque volet coché, le tout confirmé avec son résumé. En une
    transaction : la version (préliminaire) de la Transcription et son Provenance, la précédente remplacée,
    la Relecture close, et le Contrôle au pool ; sans Contrôle, la version est finale et les propositions
    passent aux soignants."""
    tache = await _tache_a_relire(fhir, agent, tache_id)
    markdown = relecture.brouillon_de(tache)
    if markdown is None:
        raise SaisieRefusee("tâche à ouvrir avant de la confirmer")
    document = await _document(fhir, tache)
    resume = resume.strip()
    refus = _a_reprendre(markdown, len(document.get("content", [])), volets_verifies, resume)
    if refus:
        raise refus
    patient = relecture.patient_de(tache) or ""
    binary = await fhir.creer(relecture.binary_de_transcription(markdown, patient))
    precedente_id = relecture.transcription_de(tache)
    precedente = await fhir.lire("DocumentReference", precedente_id) if precedente_id else None
    controlee = random.random() < part_controlee()
    cible = {"reference": f"urn:uuid:{uuid.uuid4()}"}
    ecritures = [
        _nouvelle(
            cible,
            relecture.transcription(
                scan=document,
                auteurs=[agent.sub],
                binary=binary["id"],
                taille=len(markdown.encode()),
                relue=not controlee,
                precedente=precedente_id,
            ),
        ),
        _creee(
            relecture.provenance_de_relecture(
                cible=cible, scan=document["id"], relecteur=agent.sub, activite="relecture", modele=relecture.modele_de(tache)
            )
        ),
    ]
    if precedente and precedente.get("status") == "current":
        ecritures.append(ecriture_si_inchangee(relecture.remplacee(precedente), precedente))
    ecritures.append(ecriture_si_inchangee(relecture.confirmee(tache, transcription=cible, resume=resume, relue=not controlee), tache))
    controle_id = None
    if controlee:
        controle_id = f"controle-{uuid.uuid4().hex}"
        ecritures.append(ecriture(relecture.tache_de_controle(id_=controle_id, relecture=tache, transcription=cible, resume=resume)))
    else:
        validation = relecture.tache_de_validation(id_=f"validation-{uuid.uuid4().hex}", relecture=tache, transcription=cible)
        if validation:
            ecritures.append(ecriture(validation))
    try:
        await fhir.transaction(ecritures)
    except TransactionRefusee as erreur:
        journal.warning("confirmation de la tâche %s refusée par le noyau : %s", tache_id, erreur)
        raise TacheDejaFaite() from erreur
    await _tracer(fhir, agent, tache, "create")
    ecrite = await _tache(fhir, tache_id)
    journal.info("tâche %s confirmée par l'agent %s, contrôle : %s", tache_id, agent.sub, controle_id or "aucun")
    return Confirmation(
        id=tache_id,
        statut=_statut(ecrite),
        transcription=relecture.transcription_de(ecrite),
        relue=not controlee,
        controle=controle_id,
    )


async def clore_inutilisable(fhir: ClientFhir, agent: Agent, tache_id: str, raison: Raison) -> TacheResumee:
    """Un Document qui n'est pas médical, ou déjà numérisé : la Relecture est close sans Transcription.
    Rien ne rappelle le citoyen, rien ne change le Document."""
    tache = await _tache_a_relire(fhir, agent, tache_id)
    document = await _document(fhir, tache)
    suivante = relecture.inutilisable(tache, raison)
    await _ecrire(fhir, suivante, tache)
    await _tracer(fhir, agent, tache, "update")
    journal.info("tâche %s close par l'agent %s : %s", tache_id, agent.sub, raison)
    return _resumee(suivante, document)


# Le Contrôle.


async def controler(
    fhir: ClientFhir, agent: Agent, tache_id: str, *, decision: DecisionDeControle, note: str | None, jour: date
) -> Controle:
    """La décision du contrôleur, jamais l'auteur. Accepter : une version finale remplace la préliminaire,
    avec le Provenance du Contrôle, et les propositions passent aux soignants. Renvoyer : la Relecture
    revient à son relecteur, à faire, avec la note ; le brouillon reste."""
    if not acces.relit(agent):
        raise RoleRefuse()
    controle = await _tache_de(fhir, agent, tache_id)
    if relecture.etape_de(controle) != "controle":
        raise TacheDUnAutre()
    if not relecture.est_ouverte(controle):
        raise TacheDejaFaite()
    note = (note or "").strip()
    if decision == "renvoyer" and not note:
        raise SaisieRefusee("un renvoi porte sa note")
    tache = await _tache(fhir, relecture.relecture_de(controle) or "")
    if tache.get("status") != "completed" or relecture.issue_de(tache) != "confirmee":
        raise TacheDejaFaite()
    ecritures = [ecriture_si_inchangee(relecture.controlee(controle, decision), controle)]
    validation_id = None
    if decision == "accepter":
        version_id = relecture.transcription_de(controle) or ""
        version = await fhir.lire("DocumentReference", version_id)
        if not version:
            raise TacheIntrouvable()
        document = await _document(fhir, tache)
        auteurs = [id_ for a in version.get("author", []) if (id_ := id_de(a))]
        cible = {"reference": f"urn:uuid:{uuid.uuid4()}"}
        ecritures += [
            _nouvelle(
                cible,
                relecture.transcription(
                    scan=document,
                    auteurs=[*auteurs, agent.sub],
                    binary=relecture.binary_de(version) or "",
                    taille=int(next(iter(version.get("content", [])), {}).get("attachment", {}).get("size", 0)),
                    relue=True,
                    precedente=version_id,
                ),
            ),
            _creee(
                relecture.provenance_de_relecture(cible=cible, scan=document["id"], relecteur=agent.sub, activite="controle", modele=None)
            ),
            ecriture_si_inchangee(relecture.remplacee(version), version),
            ecriture_si_inchangee(relecture.relue(tache, cible), tache),
        ]
        validation = relecture.tache_de_validation(id_=f"validation-{uuid.uuid4().hex}", relecture=tache, transcription=cible)
        if validation:
            validation_id = validation["id"]
            ecritures.append(ecriture(validation))
    else:
        ecritures.append(ecriture_si_inchangee(relecture.renvoyee(tache, note=note, controleur=agent.sub, jour=jour), tache))
    try:
        await fhir.transaction(ecritures)
    except TransactionRefusee as erreur:
        journal.warning("contrôle de la tâche %s refusé par le noyau : %s", tache_id, erreur)
        raise TacheDejaFaite() from erreur
    await _tracer(fhir, agent, controle, "update")
    journal.info("tâche %s contrôlée par l'agent %s : %s", tache_id, agent.sub, decision)
    finale = relecture.transcription_de(await _tache(fhir, tache["id"])) if decision == "accepter" else None
    return Controle(id=tache_id, decision=decision, transcription=finale, validation=validation_id)


# Le suivi de l'agent de relecture.


async def suivi(fhir: ClientFhir, agent: Agent, jour: date) -> Suivi:
    """Ma semaine (à relire, confirmées, renvoyées, contrôlées) et l'historique des Relectures et Contrôles
    faits. Rien du patient ni du Document : des comptes et des dates."""
    if not acces.relit(agent):
        raise RoleRefuse()
    taches = await fhir.chercher(
        "Task", {"owner": f"Practitioner/{agent.sub}", "_elements": "code,status,businessStatus,executionPeriod,note"}
    )
    cette_semaine = relecture.semaine(jour)

    def de_la_semaine(instant: str | None) -> bool:
        try:
            return bool(instant) and relecture.semaine(date.fromisoformat(str(instant)[:10])) == cette_semaine
        except ValueError:
            return False

    relectures = [t for t in taches if relecture.etape_de(t) == "relecture"]
    controles = [t for t in taches if relecture.etape_de(t) == "controle"]
    semaine = Semaine(
        a_relire=sum(1 for t in relectures if relecture.est_ouverte(t)),
        confirmees=sum(
            1 for t in relectures if relecture.issue_de(t) in ("confirmee", "relue") and de_la_semaine(relecture.fin_de(t))
        ),
        renvoyees=sum(1 for t in relectures for n in relecture.notes_de_controle(t) if de_la_semaine(n.date)),
        controlees=sum(1 for t in controles if t.get("status") == "completed" and de_la_semaine(relecture.fin_de(t))),
    )
    historique = [
        Evenement(id=t["id"], etape=relecture.etape_de(t) or "relecture", date=fin, issue=relecture.issue_de(t))
        for t in [*relectures, *controles]
        if not relecture.est_ouverte(t) and (fin := relecture.fin_de(t))
    ]
    historique.sort(key=lambda e: e.date, reverse=True)
    return Suivi(semaine=semaine, historique=historique[:HISTORIQUE])


# La validation clinique, par un soignant.

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
        brouillon = relecture.proposition_de(tache, proposition) or {}
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
        ecritures.append(_nouvelle(cible, verifiee_par(entree, agent)))
        ecritures.append(_creee(relecture.provenance_d_extraction(cible=cible, scan=scan, soignant=agent.sub, modele=modele)))
    suivante = relecture.apres_validation(tache, {k: v.decision for k, v in decisions.items()}, agent.sub, cibles)
    ecritures.append(ecriture_si_inchangee(suivante, tache))
    try:
        await fhir.transaction(ecritures)
    except TransactionRefusee as erreur:
        journal.warning("validation de la tâche %s refusée par le noyau : %s", tache_id, erreur)
        raise TacheDejaFaite() from erreur
    await _tracer(fhir, agent, tache, "create")
    # Le noyau a remplacé chaque `urn:uuid:` par l'identifiant de l'entrée écrite.
    entrees = [_type_et_id(ref) for ref in relecture.entrees_validees(await _tache(fhir, tache_id))]
    retenues = len(cibles)
    journal.info("tâche %s validée par le soignant %s : %d retenues", tache_id, agent.sub, retenues)
    return Validation(
        id=tache_id,
        entrees=[EntreeEcrite(type=type_, id=id_) for type_, id_ in entrees if type_ and id_],
        rejetees=len(tache.get("contained", [])) - retenues,
    )
