"""Service identite : ses routes sous /api/identite. Il ne parle jamais FHIR et n'est pas sur le réseau du noyau.

Il connecte les agents, les officines et les citoyens, et pose les deux cookies de leur session sur le
sous-domaine de l'application où ils se connectent (ADR 0004) : `__Host-session`, le jeton, et
`__Host-renouvellement`, l'identifiant de la session qui le renouvelle. Il émet les codes carnet
(ADR 0005). Sa base, ses règles et son guichet font le reste ; les routes n'y ajoutent que HTTP.
"""

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, FastAPI, Form, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, StringConstraints

from commun.jeton import COOKIE_DE_SESSION, Agent, Porteur
from commun.service import creer_service
from identite import demonstration
from identite.base import BaseDIdentite
from identite.demonstration import CitoyenDeDemonstration, CompteDeDemonstration
from identite.guichet import Guichet, Refus, SessionAgent, SessionCitoyen, SessionOfficine, SessionOuverte
from identite.jetons import SignataireDeJetons
from identite.regles.applications import Application, application_de_l_hote, origine
from identite.regles.code_carnet import NPI, ROLES_QUI_EMETTENT_UN_CODE

SERVICE = "identite"
COOKIE_DE_RENOUVELLEMENT = "__Host-renouvellement"

logging.basicConfig(level=logging.WARNING, format="%(name)s : %(message)s")
logging.getLogger(SERVICE).setLevel(logging.INFO)

DOMAINE = os.environ.get("LAFIA_DOMAINE", "")
# La clé privée est lue au démarrage : sans elle, hors de localhost, le service ne démarre pas.
signataire = SignataireDeJetons.depuis_environnement()
jetons = signataire.verificateur()
soignant_connecte = jetons.agent(ROLES_QUI_EMETTENT_UN_CODE)


@asynccontextmanager
async def cycle_de_vie(app: FastAPI) -> AsyncIterator[None]:
    """Ouvre la base, y charge le jeu de démonstration, puis ouvre le guichet."""
    if not DOMAINE:
        raise RuntimeError("LAFIA_DOMAINE manquant : domaine de base des applications.")
    base = await BaseDIdentite.ouvrir()
    await demonstration.charger(base)
    app.state.guichet = Guichet(base, signataire)
    yield
    await base.fermer()


def guichet_ouvert(request: Request) -> Guichet:
    """Dépendance : le guichet, ouvert au démarrage."""
    guichet: Guichet = request.app.state.guichet
    return guichet


def application_de_la_requete(request: Request) -> Application:
    """Dépendance : l'application de l'hôte de la requête. 404 quand l'hôte n'en désigne aucune."""
    application = application_de_l_hote(request.headers.get("host", ""), DOMAINE)
    if application is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="aucune application à cette adresse")
    return application


def formulaire_de_l_application(
    request: Request, application: Application = Depends(application_de_la_requete)
) -> Application:
    """Dépendance d'un formulaire : l'application, s'il vient de ses propres pages. 403 sinon, pour
    qu'une page hostile ne connecte personne sous le compte d'un autre."""
    if request.headers.get("origin") != origine(application, DOMAINE):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="formulaire venu d'une autre origine")
    return application


def adresse_source(request: Request) -> str:
    """L'adresse du client, que la passerelle transmet dans X-Forwarded-For. Caddy remplace celle
    qu'enverrait le client : il ne fait confiance à aucun mandataire en amont."""
    transmise = request.headers.get("x-forwarded-for", "").rsplit(",", 1)[-1].strip()
    return transmise or (request.client.host if request.client else "inconnue")


def _poser_les_cookies(reponse: Response, session: SessionOuverte) -> None:
    for nom, valeur, duree in (
        (COOKIE_DE_SESSION, session.jeton, session.duree_du_jeton),
        (COOKIE_DE_RENOUVELLEMENT, session.identifiant, session.duree_restante),
    ):
        reponse.set_cookie(
            nom, valeur, max_age=int(duree.total_seconds()), path="/", secure=True, httponly=True, samesite="strict"
        )


def _effacer_les_cookies(reponse: Response) -> None:
    for nom in (COOKIE_DE_SESSION, COOKIE_DE_RENOUVELLEMENT):
        reponse.delete_cookie(nom, path="/", secure=True, httponly=True, samesite="strict")


def _issue_de_la_connexion(resultat: SessionOuverte | Refus) -> RedirectResponse:
    """Vers l'accueil avec les deux cookies ; ou vers la page de connexion, avec la raison du refus."""
    if isinstance(resultat, Refus):
        return RedirectResponse(f"/connexion?erreur={resultat}", status_code=status.HTTP_303_SEE_OTHER)
    reponse = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    _poser_les_cookies(reponse, resultat)
    return reponse


REDIRECTIONS_DE_CONNEXION: dict[int | str, dict[str, object]] = {
    303: {"description": "Vers `/` avec les deux cookies ; ou vers `/connexion?erreur=identifiants|application|verrouille`."},
    403: {"description": "Formulaire venu d'une autre origine que l'application."},
}

routes = APIRouter()


@routes.post("/connexion", status_code=status.HTTP_303_SEE_OTHER, responses=REDIRECTIONS_DE_CONNEXION)
async def connexion(
    identifiant: Annotated[str, Form()] = "",
    mot_de_passe: Annotated[str, Form()] = "",
    application: Application = Depends(formulaire_de_l_application),
    adresse: str = Depends(adresse_source),
    guichet: Guichet = Depends(guichet_ouvert),
) -> RedirectResponse:
    """Connecte un agent ou une officine sur l'application dont vient le formulaire."""
    return _issue_de_la_connexion(await guichet.connecter(identifiant, mot_de_passe, application, adresse))


@routes.post("/citoyen/connexion", status_code=status.HTTP_303_SEE_OTHER, responses=REDIRECTIONS_DE_CONNEXION)
async def connexion_citoyen(
    npi: Annotated[str, Form()] = "",
    code: Annotated[str, Form()] = "",
    application: Application = Depends(formulaire_de_l_application),
    adresse: str = Depends(adresse_source),
    guichet: Guichet = Depends(guichet_ouvert),
) -> RedirectResponse:
    """Connecte un citoyen par son NPI et son code carnet, sur l'application citoyen seulement. Un NPI
    inconnu et un mauvais code reçoivent la même réponse."""
    return _issue_de_la_connexion(await guichet.connecter_citoyen(npi, code, application, adresse))


@routes.post(
    "/session/renouveler",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={401: {"description": "Session finie, fermée ou inconnue : les deux cookies sont effacés."}},
)
async def renouveler(
    application: Application = Depends(application_de_la_requete),
    identifiant_de_session: Annotated[str | None, Cookie(alias=COOKIE_DE_RENOUVELLEMENT)] = None,
    guichet: Guichet = Depends(guichet_ouvert),
) -> Response:
    """Un nouveau jeton, depuis le cookie de renouvellement. L'application l'appelle avant de rendre une
    page quand le jeton a expiré ; un renouvellement compte comme une activité."""
    session = await guichet.renouveler(identifiant_de_session, application) if identifiant_de_session else None
    if session is None:
        refus = JSONResponse({"detail": "session terminée"}, status_code=status.HTTP_401_UNAUTHORIZED)
        _effacer_les_cookies(refus)
        return refus
    reponse = Response(status_code=status.HTTP_204_NO_CONTENT)
    _poser_les_cookies(reponse, session)
    return reponse


@routes.post(
    "/deconnexion",
    status_code=status.HTTP_303_SEE_OTHER,
    responses={
        303: {"description": "Vers `/connexion`, les deux cookies effacés."},
        403: {"description": "Formulaire venu d'une autre origine que l'application."},
    },
)
async def deconnexion(
    _application: Application = Depends(formulaire_de_l_application),
    identifiant_de_session: Annotated[str | None, Cookie(alias=COOKIE_DE_RENOUVELLEMENT)] = None,
    guichet: Guichet = Depends(guichet_ouvert),
) -> RedirectResponse:
    """Ferme la session : plus aucun jeton n'en sera renouvelé. Le jeton en cours expire de lui-même."""
    if identifiant_de_session:
        await guichet.deconnecter(identifiant_de_session)
    reponse = RedirectResponse("/connexion", status_code=status.HTTP_303_SEE_OTHER)
    _effacer_les_cookies(reponse)
    return reponse


@routes.get(
    "/session",
    responses={401: {"description": "Jeton absent, mal formé, expiré ou mal signé, ou d'un compte inconnu."}},
)
async def session(
    porteur: Porteur = Depends(jetons.porteur), guichet: Guichet = Depends(guichet_ouvert)
) -> SessionAgent | SessionOfficine | SessionCitoyen:
    """Le porteur du jeton, tel que son application l'affiche : un agent, son nom et son établissement ;
    une officine, son nom ; un citoyen, son seul identifiant, jamais son NPI."""
    presente = await guichet.presenter(porteur)
    if presente is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="aucun compte pour ce jeton")
    return presente


class DemandeDeCode(BaseModel):
    npi: Annotated[str, StringConstraints(pattern=rf"^{NPI.pattern}$")]


class CodeCarnet(BaseModel):
    code: str
    """À imprimer sur le reçu : identite n'en garde que l'empreinte, et ne le montre plus jamais."""


@routes.post(
    "/codes-carnet",
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"description": "Jeton absent, mal formé, expiré ou mal signé."},
        403: {"description": "Un autre rôle que médecin ou infirmier."},
        422: {"description": "NPI mal formé : treize chiffres."},
    },
)
async def codes_carnet(
    demande: DemandeDeCode, soignant: Agent = Depends(soignant_connecte), guichet: Guichet = Depends(guichet_ouvert)
) -> CodeCarnet:
    """Un nouveau code carnet pour le reçu du patient : il remplace le précédent de ce NPI (ADR 0005)."""
    return CodeCarnet(code=await guichet.emettre_code(demande.npi, soignant))


@routes.get("/comptes-de-demonstration")
async def comptes_de_demonstration(
    application: Application = Depends(application_de_la_requete),
) -> list[CompteDeDemonstration | CitoyenDeDemonstration]:
    """Les comptes de démonstration des rôles que l'application connecte, et leurs mots de passe,
    publics : tout le jeu est synthétique. Jamais ceux réservés aux tests."""
    return demonstration.comptes_de_demonstration(application)


app = creer_service(SERVICE, routes, parle_fhir=False, cycle_de_vie=cycle_de_vie)
