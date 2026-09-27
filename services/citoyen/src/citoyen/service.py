"""Service citoyen : ses routes sous /api/citoyen. /sante et le client du noyau viennent de `commun`.

Le carnet ne s'ouvre que sur le NPI du jeton, jamais sur un NPI demandé : un citoyen ne voit que le sien.
Chaque lecture laisse un `AuditEvent`, motif `citoyen`, au nom du patient lui-même.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status

from citoyen.regles import carnet, documents
from citoyen.regles.acces import SessionCitoyen, session_du_citoyen
from commun.fhir import documents as fhir_documents
from commun.fhir import dossier as dossier_fhir
from commun.fhir.citoyen import DossierDuCitoyen, lire_dossier
from commun.fhir.client import ClientFhir, Ressource
from commun.jeton import Citoyen, VerificateurDeJetons
from commun.service import client_fhir, creer_service

SERVICE = "citoyen"
journal = logging.getLogger(SERVICE)

# La clé publique est lue au démarrage : sans elle, le service ne démarre pas.
jetons = VerificateurDeJetons.depuis_environnement()
citoyen_connecte = jetons.citoyen()

routes = APIRouter()

REFUS = {
    401: {"description": "Jeton absent, mal formé, expiré ou mal signé."},
    403: {"description": "Jeton d'un agent ou d'une officine : le service citoyen ne sert que le citoyen."},
}
CARNET_INTROUVABLE = {404: {"description": "Aucun dossier au noyau pour le NPI du jeton."}}


@routes.get("/session", responses=REFUS)
async def session(citoyen: Citoyen = Depends(citoyen_connecte)) -> SessionCitoyen:
    """Le citoyen connecté : son identifiant et son rôle, lus de son jeton vérifié. Jamais son NPI."""
    return session_du_citoyen(citoyen)


async def dossier_du_citoyen(
    citoyen: Citoyen = Depends(citoyen_connecte), fhir: ClientFhir = Depends(client_fhir)
) -> DossierDuCitoyen:
    """Dépendance : le dossier du NPI du jeton, lu au noyau, et l'accès tracé."""
    patient = await dossier_fhir.patient_par_npi(fhir, citoyen.npi)
    if patient is None:
        journal.info("carnet introuvable pour le citoyen %s", citoyen.sub)
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="carnet introuvable")
    lu = await lire_dossier(fhir, patient)
    await dossier_fhir.tracer(
        fhir,
        patient=patient["id"],
        qui=dossier_fhir.reference("Patient", patient["id"]),
        service=SERVICE,
        action="read",
        motif="citoyen",
    )
    return lu


@routes.get("/carnet", responses={**REFUS, **CARNET_INTROUVABLE})
async def accueil(dossier: DossierDuCitoyen = Depends(dossier_du_citoyen)) -> carnet.Accueil:
    """L'accueil du carnet : le nom, les cas en cours, l'ordonnance à suivre, le prochain moment du
    traitement, le dernier accès d'un tiers."""
    return carnet.accueil(dossier, datetime.now(timezone.utc))


@routes.get("/cas", responses={**REFUS, **CARNET_INTROUVABLE})
async def cas(dossier: DossierDuCitoyen = Depends(dossier_du_citoyen)) -> list[carnet.ResumeDeCas]:
    """Les cas de visite du citoyen, en cours d'abord."""
    return carnet.liste_des_cas(dossier)


@routes.get("/cas/{id_}", responses={**REFUS, 404: {"description": "Pas un cas de ce citoyen."}})
async def un_cas(id_: str, dossier: DossierDuCitoyen = Depends(dossier_du_citoyen)) -> carnet.DetailDeCas:
    """Un cas et ses visites : date, établissement, soignant, motif, mesures, diagnostic en mots simples."""
    detail = carnet.detail_du_cas(dossier, id_)
    if detail is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="cas introuvable")
    return detail


@routes.get("/ordonnances", responses={**REFUS, **CARNET_INTROUVABLE})
async def ordonnances(dossier: DossierDuCitoyen = Depends(dossier_du_citoyen)) -> list[carnet.OrdonnanceLue]:
    """Les ordonnances, la plus récente d'abord, chaque ligne à payer, payée, à retirer, retirée en
    partie ou retirée, avec son unité ; `arret_allergie` quand le pharmacien l'a arrêtée pour une allergie."""
    return carnet.ordonnances(dossier)


@routes.get("/traitement", responses={**REFUS, **CARNET_INTROUVABLE})
async def traitement(dossier: DossierDuCitoyen = Depends(dossier_du_citoyen)) -> carnet.TraitementDuJour:
    """Ce qu'il y a à prendre aujourd'hui, par moment : matin, midi, soir, nuit."""
    maintenant = datetime.now(carnet.FUSEAU)
    return carnet.traitement_du_jour(dossier, maintenant.date(), maintenant.hour)


@routes.get("/ma-sante", responses={**REFUS, **CARNET_INTROUVABLE})
async def ma_sante(dossier: DossierDuCitoyen = Depends(dossier_du_citoyen)) -> carnet.MaSante:
    """Ce qui dure au-delà de chaque cas : groupe sanguin, allergies, antécédents médicaux, chirurgicaux
    et familiaux, traitements au long cours. En lecture seule : seul un soignant les écrit."""
    return carnet.ma_sante(dossier)


@routes.get("/acces", responses={**REFUS, **CARNET_INTROUVABLE})
async def acces(dossier: DossierDuCitoyen = Depends(dossier_du_citoyen)) -> list[carnet.AccesLu]:
    """Qui a ouvert le dossier, quand et pourquoi ; un accès d'urgence avec son motif ; chaque dépôt de
    papiers numérisés, et où."""
    return carnet.journal_des_acces(dossier)


async def patient_du_citoyen(
    citoyen: Citoyen = Depends(citoyen_connecte), fhir: ClientFhir = Depends(client_fhir)
) -> Ressource:
    """Dépendance : le Patient du NPI du jeton, sans lire tout le dossier."""
    patient = await dossier_fhir.patient_par_npi(fhir, citoyen.npi)
    if patient is None:
        journal.info("carnet introuvable pour le citoyen %s", citoyen.sub)
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="carnet introuvable")
    return patient


async def _tracer_lecture(fhir: ClientFhir, patient: str, ressource: dict[str, str] | None = None) -> None:
    await dossier_fhir.tracer(
        fhir,
        patient=patient,
        qui=dossier_fhir.reference("Patient", patient),
        service=SERVICE,
        action="read",
        motif="citoyen",
        ressource=ressource,
    )


@routes.get("/documents", responses={**REFUS, **CARNET_INTROUVABLE})
async def mes_documents(
    patient: Ressource = Depends(patient_du_citoyen), fhir: ClientFhir = Depends(client_fhir)
) -> list[documents.DocumentLu]:
    """Mes documents : les papiers numérisés, du plus récent au plus ancien, avec leur type, leur année
    et leur nombre de pages. Numérisés, non vérifiés."""
    trouves = await fhir_documents.documents_du_patient(fhir, patient["id"])
    await _tracer_lecture(fhir, patient["id"])
    return [documents.document_lu(d) for d in trouves]


@routes.get(
    "/documents/{document_id}/pages/{rang}",
    responses={**REFUS, 404: {"description": "Pas un document de ce citoyen, ou pas de cette page."}},
    response_class=Response,
)
async def page_de_mon_document(
    document_id: str,
    rang: int,
    patient: Ressource = Depends(patient_du_citoyen),
    fhir: ClientFhir = Depends(client_fhir),
) -> Response:
    """Les octets d'une page d'un de mes documents (à partir de 1) : JPEG, PNG ou PDF."""
    document = await fhir.lire("DocumentReference", document_id)
    if document is None or not documents.est_du_citoyen(document, patient["id"]):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="document introuvable")
    page = await fhir_documents.page(fhir, document, rang)
    if page is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="page introuvable")
    await _tracer_lecture(fhir, patient["id"], dossier_fhir.reference("DocumentReference", document_id))
    return Response(
        content=page.octets,
        media_type=page.format,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


app = creer_service(SERVICE, routes, parle_fhir=True)
