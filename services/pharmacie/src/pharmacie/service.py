"""Service pharmacie : ses routes sous /api/pharmacie. /sante et le client du noyau viennent de `commun`."""

from fastapi import APIRouter, Depends

from commun.jeton import Agent, Officine, VerificateurDeJetons
from commun.service import creer_service
from pharmacie.regles.acces import ROLES_ADMIS

SERVICE = "pharmacie"

# La clé publique est lue au démarrage : sans elle, le service ne démarre pas.
jetons = VerificateurDeJetons.depuis_environnement()
pharmacien_ou_officine_connecte = jetons.agent_ou_officine(ROLES_ADMIS)

routes = APIRouter()


@routes.get(
    "/session",
    responses={
        401: {"description": "Jeton absent, mal formé, expiré ou mal signé."},
        403: {"description": "Rôle que le service pharmacie ne sert pas."},
    },
)
async def session(porteur: Agent | Officine = Depends(pharmacien_ou_officine_connecte)) -> Agent | Officine:
    """Le pharmacien connecté, son identifiant, son rôle et son établissement ; ou l'officine, son
    identifiant et son rôle. Lus de son jeton vérifié."""
    return porteur


app = creer_service(SERVICE, routes, parle_fhir=True)
