"""Service relecture : ses routes sous /api/relecture. /sante et le client du noyau viennent de `commun`.

Il parle FHIR au noyau, et joint le service extraction par le réseau interne `extraction` : le seul
appel d'un service à un autre, que l'ADR 0009 admet.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from pydantic import BaseModel

from commun.fhir.client import ClientFhir
from commun.fhir.relecture import DecisionDeControle, Raison
from commun.jeton import Agent, VerificateurDeJetons
from commun.service import client_fhir, creer_service
from relecture.lecteur import ExtractionIndisponible, Lecteur, lecteur
from relecture.regles import taches as regles
from relecture.regles.acces import ROLES_ADMIS
from relecture.regles.taches import (
    Confirmation,
    Controle,
    DecisionRecue,
    Enregistrement,
    Suivi,
    TacheResumee,
    TacheVue,
    Validation,
)

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
        "description": "Rôle que le service ne sert pas, ou Tâche d'un autre agent ou d'une autre étape : l'agent de "
        "relecture relit et contrôle (jamais sa propre relecture), le soignant valide."
    },
    404: {"description": "Aucune Tâche de relecture sous cet identifiant."},
    409: {"description": "La Tâche n'est plus à cette étape : confirmée, contrôlée, close, ou changée par un autre au même instant."},
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
            return HTTPException(status.HTTP_403_FORBIDDEN, detail="tâche d'un autre agent ou d'une autre étape")
        case regles.RoleRefuse():
            return HTTPException(status.HTTP_403_FORBIDDEN, detail="rôle qui ne fait pas cette étape")
        case regles.TacheDejaFaite():
            return HTTPException(status.HTTP_409_CONFLICT, detail="tâche plus à cette étape")
        case regles.VersionPerimee():
            return HTTPException(status.HTTP_409_CONFLICT, detail="transcription enregistrée depuis : relire la tâche")
        case regles.VersionAbsente():
            return HTTPException(status.HTTP_428_PRECONDITION_REQUIRED, detail="If-Match attendu : la version de la tâche lue")
        case regles.TranscriptionRefusee():
            return HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "message": "transcription à reprendre",
                    "erreurs": erreur.erreurs,
                    "volets_non_verifies": erreur.volets_non_verifies,
                },
            )
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
    regles.VersionPerimee,
    regles.VersionAbsente,
    regles.TranscriptionRefusee,
    regles.SaisieRefusee,
    ExtractionIndisponible,
)


def _etiquette(version: str) -> str:
    return f'W/"{version}"'


@routes.get("/session", responses=REFUS)
async def session(agent: Agent = Depends(agent_connecte)) -> Agent:
    """Le relecteur connecté : son identifiant, son rôle et son établissement, lus de son jeton vérifié."""
    return agent


@routes.get("/taches", responses=REFUS)
async def mes_taches(agent: Agent = Depends(agent_connecte), fhir: ClientFhir = Depends(client_fhir)) -> list[TacheResumee]:
    """Les Tâches de l'appelant. Agent de relecture : sa semaine, Relectures et Contrôles, complétée jusqu'à
    son quota depuis les pools, jamais de son département. Soignant : les Tâches de validation qu'il a
    prises, et quelques libres."""
    return await regles.mes_taches(fhir, agent, aujourd_hui().date())


@routes.get("/suivi", responses=REFUS)
async def suivi(agent: Agent = Depends(agent_connecte), fhir: ClientFhir = Depends(client_fhir)) -> Suivi:
    """Ma semaine d'agent de relecture (à relire, confirmées, renvoyées par le Contrôle, contrôlées) et
    l'historique de mes Relectures et Contrôles. Un soignant : 403."""
    try:
        return await regles.suivi(fhir, agent, aujourd_hui().date())
    except ERREURS as erreur:
        raise _refus(erreur) from erreur


@routes.get(
    "/taches/{tache_id}",
    responses={**REFUS_DE_LA_TACHE, 503: {"description": "Première ouverture : le service extraction n'a pas répondu."}},
)
async def lire_tache(
    tache_id: str,
    response: Response,
    agent: Agent = Depends(agent_connecte),
    fhir: ClientFhir = Depends(client_fhir),
    lecture: Lecteur = Depends(lecteur),
) -> TacheVue:
    """Une Tâche : le Document (type, année, pages), jamais qui est le patient ; la Transcription en Markdown
    et ses volets, le texte lu, le modèle, les notes du Contrôle, le résumé du relecteur ; à la validation,
    les propositions. Une Relecture ouverte pour la première fois est d'abord lue par l'Extraction. Un
    soignant qui ouvre une Tâche de validation libre la prend. L'en-tête ETag porte la version de la Tâche."""
    try:
        vue = await regles.lire_tache(fhir, lecture, agent, tache_id)
    except ERREURS as erreur:
        raise _refus(erreur) from erreur
    response.headers["ETag"] = _etiquette(vue.version)
    response.headers["Cache-Control"] = "no-store"
    return vue


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


class TranscriptionRecue(BaseModel):
    """Le brouillon corrigé, en Markdown restreint par volets (ADR 0010)."""

    markdown: str


@routes.put(
    "/taches/{tache_id}/transcription",
    responses={
        **REFUS_DE_LA_TACHE,
        409: {"description": "La Tâche a changé depuis la version d'If-Match, ou n'est plus à relire."},
        422: {"description": "Plus de 200 Ko, ou Tâche jamais ouverte."},
        428: {"description": "Sans If-Match."},
    },
)
async def enregistrer(
    tache_id: str,
    recue: TranscriptionRecue,
    response: Response,
    si_version: str | None = Header(default=None, alias="If-Match"),
    agent: Agent = Depends(agent_connecte),
    fhir: ClientFhir = Depends(client_fhir),
) -> Enregistrement:
    """Enregistre le brouillon du relecteur dans sa Relecture : ce n'est pas encore une version de la
    Transcription. `If-Match` porte la version lue (ETag de `GET /taches/{id}`) ; la nouvelle revient en ETag."""
    try:
        enregistrement = await regles.enregistrer(fhir, agent, tache_id, recue.markdown, si_version)
    except ERREURS as erreur:
        raise _refus(erreur) from erreur
    response.headers["ETag"] = _etiquette(enregistrement.version)
    return enregistrement


class ConfirmationRecue(BaseModel):
    """Les rangs des volets cochés, vérifiés contre leurs pages, et le résumé des changements."""

    volets_verifies: list[int]
    resume: str


@routes.post(
    "/taches/{tache_id}/confirmation",
    responses={
        **REFUS_DE_LA_TACHE,
        422: {"description": "Volet non coché, Markdown hors de l'ADR 0010, résumé manquant : `detail` les liste."},
    },
)
async def confirmer(
    tache_id: str, recue: ConfirmationRecue, agent: Agent = Depends(agent_connecte), fhir: ClientFhir = Depends(client_fhir)
) -> Confirmation:
    """La double confirmation du relecteur : une version de la Transcription, son Provenance, et le Contrôle
    au pool, pour un autre agent de relecture."""
    try:
        return await regles.confirmer(fhir, agent, tache_id, volets_verifies=recue.volets_verifies, resume=recue.resume)
    except ERREURS as erreur:
        raise _refus(erreur) from erreur


class ControleRecu(BaseModel):
    decision: DecisionDeControle
    note: str | None = None
    """Ce que le relecteur doit reprendre : exigée pour un renvoi."""


@routes.post(
    "/taches/{tache_id}/controle",
    responses={**REFUS_DE_LA_TACHE, 422: {"description": "Renvoi sans note."}},
)
async def controler(
    tache_id: str, recu: ControleRecu, agent: Agent = Depends(agent_connecte), fhir: ClientFhir = Depends(client_fhir)
) -> Controle:
    """Le Contrôle : accepter rend la Transcription relue (version finale, Provenance du Contrôle, propositions
    aux soignants) ; renvoyer rend la Relecture à son relecteur, avec la note."""
    try:
        return await regles.controler(fhir, agent, tache_id, decision=recu.decision, note=recu.note, jour=aujourd_hui().date())
    except ERREURS as erreur:
        raise _refus(erreur) from erreur


class InutilisableRecu(BaseModel):
    raison: Raison


@routes.post("/taches/{tache_id}/inutilisable", responses=REFUS_DE_LA_TACHE)
async def inutilisable(
    tache_id: str, recu: InutilisableRecu, agent: Agent = Depends(agent_connecte), fhir: ClientFhir = Depends(client_fhir)
) -> TacheResumee:
    """Un Document qui n'est pas médical, ou déjà numérisé : la Relecture est close sans Transcription. Rien
    ne contacte le citoyen."""
    try:
        return await regles.clore_inutilisable(fhir, agent, tache_id, recu.raison)
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
