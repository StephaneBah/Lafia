"""Service caisse : ses routes sous /api/caisse. /sante et le client du noyau viennent de `commun`."""

from fastapi import APIRouter, Depends

from caisse.regles.acces import ROLES_ADMIS
from commun.jeton import Agent, VerificateurDeJetons
from commun.service import creer_service

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


app = creer_service(SERVICE, routes, parle_fhir=True)
