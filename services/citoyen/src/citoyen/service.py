"""Service citoyen : ses routes sous /api/citoyen. /sante et le client du noyau viennent de `commun`."""

from fastapi import APIRouter, Depends

from citoyen.regles.acces import SessionCitoyen, session_du_citoyen
from commun.jeton import Citoyen, VerificateurDeJetons
from commun.service import creer_service

SERVICE = "citoyen"

# La clé publique est lue au démarrage : sans elle, le service ne démarre pas.
jetons = VerificateurDeJetons.depuis_environnement()
citoyen_connecte = jetons.citoyen()

routes = APIRouter()


@routes.get(
    "/session",
    responses={
        401: {"description": "Jeton absent, mal formé, expiré ou mal signé."},
        403: {"description": "Jeton d'un agent : le service citoyen ne sert que le citoyen."},
    },
)
async def session(citoyen: Citoyen = Depends(citoyen_connecte)) -> SessionCitoyen:
    """Le citoyen connecté : son identifiant et son rôle, lus de son jeton vérifié. Jamais son NPI."""
    return session_du_citoyen(citoyen)


app = creer_service(SERVICE, routes, parle_fhir=True)
