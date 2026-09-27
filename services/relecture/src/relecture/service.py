"""Service relecture : ses routes sous /api/relecture. /sante et le client du noyau viennent de `commun`.

Il parle FHIR au noyau, et joint le service extraction par le réseau interne `extraction` : le seul
appel d'un service à un autre, que l'ADR 0009 admet.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from commun.fhir.client import ClientFhir
from commun.fhir.relecture import Verdict
from commun.jeton import Agent, VerificateurDeJetons
from commun.service import client_fhir, creer_service
from relecture.lecteur import ExtractionIndisponible, Lecteur, lecteur
from relecture.regles import taches as regles
from relecture.regles.acces import ROLES_ADMIS
from relecture.regles.taches import DecisionRecue, TacheResumee, TacheVue, Validation

SERVICE = "relecture"

# La clé publique est lue au démarrage : sans elle, le service ne démarre pas.
jetons = VerificateurDeJetons.depuis_environnement()
agent_connecte = jetons.agent(ROLES_ADMIS)

routes = APIRouter()

REFUS = {
    401: {"description": "Jeton absent, mal formé, expiré ou mal signé."},
    403: {"description": "Rôle que le service relecture ne sert pas."},
}
REFUS_DE_LA_TACHE = {
    **REFUS,
    403: {
        "description": "Rôle que le service ne sert pas, ou Tâche d'un autre relecteur, ou d'une autre étape : "
        "l'agent de relecture trie, le soignant valide."
    },
    404: {"description": "Aucune Tâche de relecture sous cet identifiant."},
    409: {"description": "La Tâche n'est plus à cette étape : déjà triée, déjà validée, ou prise par un autre."},
}


def aujourd_hui() -> datetime:
    return datetime.now(timezone.utc)


def _refus(erreur: Exception) -> HTTPException:
    match erreur:
        case regles.TacheIntrouvable():
            return HTTPException(status.HTTP_404_NOT_FOUND, detail="tâche introuvable")
        case regles.PageIntrouvable():
            return HTTPException(status.HTTP_404_NOT_FOUND, detail="page introuvable")
        case regles.TacheDUnAutre():
            return HTTPException(status.HTTP_403_FORBIDDEN, detail="tâche d'un autre relecteur ou d'une autre étape")
        case regles.RoleRefuse():
            return HTTPException(status.HTTP_403_FORBIDDEN, detail="rôle qui ne fait pas cette étape")
        case regles.TacheDejaFaite():
            return HTTPException(status.HTTP_409_CONFLICT, detail="tâche plus à cette étape")
        case regles.SaisieRefusee():
            return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(erreur))
        case ExtractionIndisponible():
            return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="extraction indisponible, réessayer")
    raise erreur


ERREURS = (
    regles.TacheIntrouvable,
    regles.PageIntrouvable,
    regles.TacheDUnAutre,
    regles.RoleRefuse,
    regles.TacheDejaFaite,
    regles.SaisieRefusee,
    ExtractionIndisponible,
)


@routes.get("/session", responses=REFUS)
async def session(agent: Agent = Depends(agent_connecte)) -> Agent:
    """Le relecteur connecté : son identifiant, son rôle et son établissement, lus de son jeton vérifié."""
    return agent


@routes.get("/taches", responses=REFUS)
async def mes_taches(agent: Agent = Depends(agent_connecte), fhir: ClientFhir = Depends(client_fhir)) -> list[TacheResumee]:
    """Les Tâches de l'appelant. Agent de relecture : sa semaine, complétée jusqu'à son quota par des
    Documents d'autres départements. Soignant : les Tâches de validation qu'il a prises, et quelques libres."""
    return await regles.mes_taches(fhir, agent, aujourd_hui().date())


@routes.get("/taches/{tache_id}", responses=REFUS_DE_LA_TACHE)
async def lire_tache(tache_id: str, agent: Agent = Depends(agent_connecte), fhir: ClientFhir = Depends(client_fhir)) -> TacheVue:
    """Une Tâche : le Document (type, année, pages, lisibilité), jamais qui est le patient. À la validation :
    les propositions, le modèle qui les a lues, le texte lu. Un soignant qui ouvre une Tâche libre la prend."""
    try:
        return await regles.lire_tache(fhir, agent, tache_id)
    except ERREURS as erreur:
        raise _refus(erreur) from erreur


@routes.get(
    "/taches/{tache_id}/pages/{rang}",
    response_class=Response,
    responses={
        **REFUS_DE_LA_TACHE,
        200: {"content": {"image/jpeg": {}, "image/png": {}, "application/pdf": {}}, "description": "La page."},
        404: {"description": "Aucune Tâche sous cet identifiant, ou aucune page à ce rang."},
    },
)
async def lire_page(
    tache_id: str, rang: int, agent: Agent = Depends(agent_connecte), fhir: ClientFhir = Depends(client_fhir)
) -> Response:
    """Les octets d'une page du Document de la Tâche, pour qui la tient. `rang` commence à 1."""
    try:
        page = await regles.lire_page(fhir, agent, tache_id, rang)
    except ERREURS as erreur:
        raise _refus(erreur) from erreur
    return Response(content=page.octets, media_type=page.format, headers={"Cache-Control": "no-store", "Content-Disposition": "inline"})


class Triage(BaseModel):
    """Le verdict, et au besoin le bon type et la bonne année du Document."""

    verdict: Verdict
    type: str | None = None
    annee: str | None = None


@routes.post(
    "/taches/{tache_id}/triage",
    responses={
        **REFUS_DE_LA_TACHE,
        422: {"description": "Verdict, type ou année inconnus."},
        503: {"description": "Le service extraction n'a pas répondu : la Tâche reste à trier."},
    },
)
async def trier(
    tache_id: str,
    triage: Triage,
    agent: Agent = Depends(agent_connecte),
    fhir: ClientFhir = Depends(client_fhir),
    lecture: Lecteur = Depends(lecteur),
) -> TacheResumee:
    """Le triage de l'agent de relecture. Utilisable : le Document est lu par l'Extraction et la Tâche passe
    à la validation des soignants. Tout autre verdict la clôt. Le Document lui-même ne change pas."""
    try:
        return await regles.trier(
            fhir, lecture, agent, tache_id, verdict=triage.verdict, type_=triage.type, annee=triage.annee, jour=aujourd_hui().date()
        )
    except ERREURS as erreur:
        raise _refus(erreur) from erreur


class ValidationRecue(BaseModel):
    """Une décision par proposition : accepter, corriger (avec la valeur juste) ou rejeter. Une proposition
    que la liste ne cite pas est rejetée."""

    propositions: list[DecisionRecue]


@routes.post(
    "/taches/{tache_id}/validation",
    responses={**REFUS_DE_LA_TACHE, 422: {"description": "Proposition inconnue, décidée deux fois, ou correction sans valeur lisible."}},
)
async def valider(
    tache_id: str, validation: ValidationRecue, agent: Agent = Depends(agent_connecte), fhir: ClientFhir = Depends(client_fhir)
) -> Validation:
    """La validation du soignant qui a pris la Tâche : les propositions retenues entrent au dossier, avec
    l'origine `extraction` et leur Provenance ; la Tâche est close."""
    try:
        return await regles.valider(fhir, agent, tache_id, validation.propositions)
    except ERREURS as erreur:
        raise _refus(erreur) from erreur


app = creer_service(SERVICE, routes, parle_fhir=True)
