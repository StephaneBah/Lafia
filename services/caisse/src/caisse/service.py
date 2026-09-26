"""Service caisse : ses routes sous /api/caisse. /sante et le client du noyau viennent de `commun`."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from caisse.regles import encaissement
from caisse.regles.acces import ROLES_ADMIS
from caisse.regles.encaissement import Ordonnance, Recepisse
from commun.fhir.client import ClientFhir
from commun.jeton import Agent, VerificateurDeJetons
from commun.service import client_fhir, creer_service

SERVICE = "caisse"

# La clé publique est lue au démarrage : sans elle, le service ne démarre pas.
jetons = VerificateurDeJetons.depuis_environnement()
caissier_connecte = jetons.agent(ROLES_ADMIS)

routes = APIRouter()


@routes.get(
    "/session",
    responses={
        401: {"description": "Jeton absent, mal formé, expiré ou mal signé."},
        403: {"description": "Rôle que le service caisse ne sert pas."},
    },
)
async def session(caissier: Agent = Depends(caissier_connecte)) -> Agent:
    """Le caissier connecté : son identifiant, son rôle et son établissement, lus de son jeton vérifié."""
    return caissier


REFUS = {
    401: {"description": "Jeton absent, mal formé, expiré ou mal signé."},
    403: {"description": "Rôle que le service caisse ne sert pas."},
}


class Encaissement(BaseModel):
    """Les lignes à encaisser, par l'identifiant que `GET /ordonnances/{numero}` leur donne."""

    lignes: list[str]


@routes.get(
    "/ordonnances/{numero}",
    responses={**REFUS, 404: {"description": "Aucune ordonnance à payer sous ce numéro dans l'établissement."}},
)
async def ordonnance(
    numero: str, caissier: Agent = Depends(caissier_connecte), fhir: ClientFhir = Depends(client_fhir)
) -> Ordonnance:
    """L'ordonnance à payer : ses lignes tarifées par l'établissement du caissier, et ce qu'il en reste à payer."""
    try:
        return await encaissement.lire_ordonnance(fhir, caissier, numero)
    except encaissement.OrdonnanceIntrouvable as erreur:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="ordonnance introuvable") from erreur


@routes.post(
    "/ordonnances/{numero}/encaissements",
    status_code=status.HTTP_201_CREATED,
    responses={
        **REFUS,
        404: {"description": "Aucune ordonnance à payer sous ce numéro dans l'établissement."},
        409: {"description": "Une ligne est déjà payée : rien n'est encaissé."},
        422: {"description": "Une ligne n'est pas de cette ordonnance, ou aucune ligne demandée."},
    },
)
async def encaisser(
    numero: str,
    demande: Encaissement,
    caissier: Agent = Depends(caissier_connecte),
    fhir: ClientFhir = Depends(client_fhir),
) -> Recepisse:
    """Encaisse des lignes de l'ordonnance, aux tarifs de l'établissement : rend le récépissé."""
    try:
        return await encaissement.encaisser(fhir, caissier, numero, demande.lignes)
    except encaissement.OrdonnanceIntrouvable as erreur:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="ordonnance introuvable") from erreur
    except encaissement.LigneDejaPayee as erreur:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="ligne déjà payée") from erreur
    except encaissement.LigneInconnue as erreur:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="ligne inconnue") from erreur


@routes.get(
    "/recepisses/{numero}",
    responses={**REFUS, 404: {"description": "Aucun récépissé sous ce numéro dans l'établissement."}},
)
async def recepisse(
    numero: str, caissier: Agent = Depends(caissier_connecte), fhir: ClientFhir = Depends(client_fhir)
) -> Recepisse:
    """Un récépissé émis par la caisse de l'établissement, pour l'imprimer ou le réimprimer."""
    try:
        return await encaissement.lire_recepisse(fhir, caissier, numero)
    except encaissement.RecepisseIntrouvable as erreur:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="récépissé introuvable") from erreur


app = creer_service(SERVICE, routes, parle_fhir=True)
