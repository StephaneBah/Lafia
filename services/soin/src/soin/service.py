"""Service soin : ses routes sous /api/soin. /sante et le client du noyau viennent de `commun`."""

from fastapi import APIRouter, Depends

from commun.jeton import Agent, VerificateurDeJetons
from commun.service import creer_service
from soin.regles.acces import ROLES_ADMIS

SERVICE = "soin"

# La clé publique est lue au démarrage : sans elle, le service ne démarre pas.
jetons = VerificateurDeJetons.depuis_environnement()
soignant_connecte = jetons.agent(ROLES_ADMIS)

routes = APIRouter()


@routes.get(
    "/session",
    responses={
        401: {"description": "Jeton absent, mal formé, expiré ou mal signé."},
        403: {"description": "Rôle que le service soin ne sert pas."},
    },
)
async def session(soignant: Agent = Depends(soignant_connecte)) -> Agent:
    """Le soignant connecté : son identifiant, son rôle et son établissement, lus de son jeton vérifié."""
    return soignant


app = creer_service(SERVICE, routes, parle_fhir=True)
