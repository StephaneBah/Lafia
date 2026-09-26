"""Service pharmacie : ses routes sous /api/pharmacie. /sante et le client du noyau viennent de `commun`."""

from fastapi import APIRouter, Depends

from commun.jeton import Agent, VerificateurDeJetons
from commun.service import creer_service
from pharmacie.regles.acces import ROLES_ADMIS

SERVICE = "pharmacie"

# La clé publique est lue au démarrage : sans elle, le service ne démarre pas.
jetons = VerificateurDeJetons.depuis_environnement()
pharmacien_connecte = jetons.agent(ROLES_ADMIS)

routes = APIRouter()


@routes.get(
    "/session",
    responses={
        401: {"description": "Jeton absent, mal formé, expiré ou mal signé."},
        403: {"description": "Rôle que le service pharmacie ne sert pas."},
    },
)
async def session(pharmacien: Agent = Depends(pharmacien_connecte)) -> Agent:
    """Le pharmacien connecté : son identifiant, son rôle et son établissement, lus de son jeton vérifié."""
    return pharmacien


app = creer_service(SERVICE, routes, parle_fhir=True)
