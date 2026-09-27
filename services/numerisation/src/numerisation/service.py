"""Service numerisation : ses routes sous /api/numerisation. /sante et le client du noyau viennent de `commun`."""

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from pydantic import BaseModel

from commun.fhir.client import ClientFhir
from commun.fhir.documents import NOTE_DE_PAPIER_ABIME_MAX, Lisibilite, PieceDIdentite, TypeDeDocument
from commun.jeton import Agent, VerificateurDeJetons
from commun.service import client_fhir, creer_service
from commun.televersement import pages_televersees
from numerisation.regles import depot as regles
from numerisation.regles.acces import ROLES_ADMIS
from numerisation.regles.depot import Cloture, Depot, DocumentAjoute, DepotOuvert

SERVICE = "numerisation"

# La clé publique est lue au démarrage : sans elle, le service ne démarre pas.
jetons = VerificateurDeJetons.depuis_environnement()
agent_connecte = jetons.agent(ROLES_ADMIS)

routes = APIRouter()

REFUS = {
    401: {"description": "Jeton absent, mal formé, expiré ou mal signé."},
    403: {"description": "Rôle que le service numerisation ne sert pas."},
}
REFUS_DU_DEPOT = {
    **REFUS,
    403: {"description": "Rôle que le service ne sert pas, ou Dépôt ouvert par un autre agent."},
    404: {"description": "Aucun Dépôt sous cet identifiant."},
    409: {"description": "Dépôt clos : plus rien ne s'y ajoute ni ne s'y lit."},
}


@routes.get("/session", responses=REFUS)
async def session(agent: Agent = Depends(agent_connecte)) -> Agent:
    """L'agent de numérisation connecté : son identifiant, son rôle et son établissement, lus de son jeton vérifié."""
    return agent


class Ouverture(BaseModel):
    """Le NPI que le citoyen donne, la pièce d'identité que l'agent a vérifiée, et si le Dépôt est de la Reprise."""

    npi: str
    piece: PieceDIdentite
    reprise: bool = False


def _refus_du_depot(erreur: Exception) -> HTTPException:
    match erreur:
        case regles.DepotIntrouvable():
            return HTTPException(status.HTTP_404_NOT_FOUND, detail="dépôt introuvable")
        case regles.DepotDUnAutreAgent():
            return HTTPException(status.HTTP_403_FORBIDDEN, detail="dépôt d'un autre agent")
        case regles.DepotClos():
            return HTTPException(status.HTTP_409_CONFLICT, detail="dépôt clos")
        case regles.DocumentIntrouvable():
            return HTTPException(status.HTTP_404_NOT_FOUND, detail="page introuvable")
        case regles.DocumentTropLourd():
            return HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, detail=str(erreur))
        case regles.DocumentRefuse():
            return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(erreur))
    raise erreur


ERREURS_DU_DEPOT = (
    regles.DepotIntrouvable,
    regles.DepotDUnAutreAgent,
    regles.DepotClos,
    regles.DocumentIntrouvable,
    regles.DocumentTropLourd,
    regles.DocumentRefuse,
)


@routes.post(
    "/depots",
    status_code=status.HTTP_201_CREATED,
    responses={**REFUS, 404: {"description": "Aucun patient sous ce NPI."}},
)
async def ouvrir(
    demande: Ouverture, agent: Agent = Depends(agent_connecte), fhir: ClientFhir = Depends(client_fhir)
) -> DepotOuvert:
    """Ouvre un Dépôt : rend son identifiant, et le nom, les prénoms et l'année de naissance du patient, à comparer à sa pièce."""
    try:
        return await regles.ouvrir(fhir, agent, demande.npi.strip(), demande.piece, demande.reprise)
    except regles.PatientIntrouvable as erreur:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="patient introuvable") from erreur


@routes.post(
    "/depots/{depot_id}/documents",
    status_code=status.HTTP_201_CREATED,
    responses={
        **REFUS_DU_DEPOT,
        413: {"description": "Plus de 20 pages, ou une page de plus de 3 Mo."},
        422: {"description": "Type, année, lisibilité ou format de page refusés (JPEG, PNG ou PDF), ou note de papier abîmé de plus de 300 caractères."},
    },
)
async def ajouter_document(
    depot_id: str,
    type: TypeDeDocument = Form(description="carnet, compte-rendu, resultat-analyse, ordonnance, imagerie, certificat, autre"),
    annee: str = Form(description="L'année du papier : 2019."),
    lisibilite: Lisibilite = Form(description="lisible ou partiel"),
    etablissement: str | None = Form(None, description="L'établissement d'origine, tel qu'écrit sur le papier."),
    papier_abime: str | None = Form(
        None,
        max_length=NOTE_DE_PAPIER_ABIME_MAX,
        description="Le papier est abîmé en lui-même : pourquoi une page a passé outre le contrôle de la capture.",
    ),
    pages: list[UploadFile] = File(default=[], description="Les pages, dans l'ordre."),
    pages_en_tableau: list[UploadFile] = File(default=[], alias="pages[]", description="Les pages, sous le nom pages[]."),
    agent: Agent = Depends(agent_connecte),
    fhir: ClientFhir = Depends(client_fhir),
) -> DocumentAjoute:
    """Numérise un Document dans le Dépôt : ses pages, son type, son année, son établissement d'origine, sa lisibilité,
    et la note de l'agent quand le papier, abîmé en lui-même, a passé outre le contrôle de la capture."""
    try:
        return await regles.ajouter_document(
            fhir,
            agent,
            depot_id,
            type_=type,
            annee=annee.strip(),
            etablissement_d_origine=etablissement,
            lisibilite=lisibilite,
            pages=await pages_televersees([*pages, *pages_en_tableau]),
            papier_abime=papier_abime,
        )
    except ERREURS_DU_DEPOT as erreur:
        raise _refus_du_depot(erreur) from erreur


@routes.get("/depots/{depot_id}", responses=REFUS_DU_DEPOT)
async def lire_depot(
    depot_id: str, agent: Agent = Depends(agent_connecte), fhir: ClientFhir = Depends(client_fhir)
) -> Depot:
    """Le Dépôt en cours : l'identité du patient au guichet, et les Documents déjà numérisés."""
    try:
        return await regles.lire_depot(fhir, agent, depot_id)
    except ERREURS_DU_DEPOT as erreur:
        raise _refus_du_depot(erreur) from erreur


@routes.get(
    "/depots/{depot_id}/documents/{document_id}/pages/{rang}",
    response_class=Response,
    responses={
        **REFUS_DU_DEPOT,
        200: {"content": {"image/jpeg": {}, "image/png": {}, "application/pdf": {}}, "description": "La page."},
        404: {"description": "Aucun Dépôt, Document de ce Dépôt ou page à ce rang."},
    },
)
async def lire_page(
    depot_id: str,
    document_id: str,
    rang: int,
    agent: Agent = Depends(agent_connecte),
    fhir: ClientFhir = Depends(client_fhir),
) -> Response:
    """Les octets d'une page d'un Document du Dépôt, pour la revoir avant de clore. `rang` commence à 1."""
    try:
        page = await regles.lire_page(fhir, agent, depot_id, document_id, rang)
    except ERREURS_DU_DEPOT as erreur:
        raise _refus_du_depot(erreur) from erreur
    return Response(
        content=page.octets,
        media_type=page.format,
        headers={"Cache-Control": "private, no-store", "Content-Disposition": "inline", "X-Content-Type-Options": "nosniff"},
    )


@routes.post("/depots/{depot_id}/cloture", responses=REFUS_DU_DEPOT)
async def clore(
    depot_id: str, agent: Agent = Depends(agent_connecte), fhir: ClientFhir = Depends(client_fhir)
) -> Cloture:
    """Clôt le Dépôt : il est enregistré avec ses Documents, et plus rien ne s'y ajoute. Les papiers retournent au citoyen."""
    try:
        return await regles.clore(fhir, agent, depot_id)
    except ERREURS_DU_DEPOT as erreur:
        raise _refus_du_depot(erreur) from erreur


app = creer_service(SERVICE, routes, parle_fhir=True)
