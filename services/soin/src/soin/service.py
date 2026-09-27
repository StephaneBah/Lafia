"""Service soin : ses routes sous /api/soin. /sante et le client du noyau viennent de `commun`.

Un patient y est désigné par l'identifiant de son Patient : le NPI n'entre qu'une fois, dans le
corps de `POST /recherche`, et n'apparaît jamais dans une adresse. Les routes traduisent HTTP : le
travail est dans `soin.dossier`, les règles dans `soin.regles`.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status

from commun.fhir.client import ClientFhir
from commun.fhir.documents import OCTETS_PAR_PAGE, Page, PageRefusee
from commun.jeton import Agent, VerificateurDeJetons
from commun.service import client_fhir, creer_service
from soin import dossier, modeles
from soin.regles.acces import ROLES_ADMIS
from soin.regles.documents import DocumentTropLourd
from soin.regles.dossier import SaisieRefusee
from soin.regles.relation import SansRelationDeSoin
from soin.regles.visite import VisiteRefusee, peut_clore

SERVICE = "soin"

# La clé publique est lue au démarrage : sans elle, le service ne démarre pas.
jetons = VerificateurDeJetons.depuis_environnement()
soignant_connecte = jetons.agent(ROLES_ADMIS)

routes = APIRouter()

REFUS = {
    401: {"description": "Jeton absent, mal formé, expiré ou mal signé."},
    403: {"description": "Rôle que le service soin ne sert pas, ou pas de relation de soin."},
    404: {"description": "Aucun patient, aucun cas ou aucun traitement sous cet identifiant."},
}
SAISIE = {**REFUS, 422: {"description": "Hors catalogue, ou saisie incomplète."}}


def _http(erreur: Exception) -> HTTPException:
    match erreur:
        case dossier.PatientInconnu():
            return HTTPException(status.HTTP_404_NOT_FOUND, "aucun patient")
        case dossier.CasInconnu():
            return HTTPException(status.HTTP_404_NOT_FOUND, "aucun cas sous cet identifiant")
        case dossier.TraitementInconnu():
            return HTTPException(status.HTTP_404_NOT_FOUND, "aucun traitement sous cet identifiant")
        case dossier.DocumentInconnu() | dossier.PageInconnue():
            return HTTPException(status.HTTP_404_NOT_FOUND, "aucun document ou aucune page sous cet identifiant")
        case DocumentTropLourd():
            return HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, str(erreur))
        case SansRelationDeSoin():
            return HTTPException(status.HTTP_403_FORBIDDEN, "pas de relation de soin")
        case dossier.CasClos():
            return HTTPException(status.HTTP_409_CONFLICT, "ce cas est clos")
        case VisiteRefusee() | SaisieRefusee() | PageRefusee():
            return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(erreur))
    raise erreur


ERREURS = (
    dossier.PatientInconnu,
    dossier.CasInconnu,
    dossier.TraitementInconnu,
    dossier.DocumentInconnu,
    dossier.PageInconnue,
    SansRelationDeSoin,
    dossier.CasClos,
    VisiteRefusee,
    SaisieRefusee,
    PageRefusee,
    DocumentTropLourd,
)


@routes.get("/session", responses=REFUS)
async def session(soignant: Agent = Depends(soignant_connecte)) -> Agent:
    """Le soignant connecté : son identifiant, son rôle et son établissement, lus de son jeton vérifié."""
    return soignant


@routes.get("/catalogue", responses=REFUS)
async def catalogue(
    soignant: Agent = Depends(soignant_connecte), fhir: ClientFhir = Depends(client_fhir)
) -> dict[str, Any]:
    """Ce qu'une visite peut porter : produits tarifés à l'établissement (avec leur forme), mesures,
    diagnostics ; et les classes d'allergie, les groupes sanguins."""
    return await dossier.catalogue(fhir, soignant.etablissement)


@routes.post("/recherche", responses=REFUS)
async def rechercher(
    demande: modeles.Recherche, soignant: Agent = Depends(soignant_connecte), fhir: ClientFhir = Depends(client_fhir)
) -> dict[str, str]:
    """Le patient qui porte ce NPI, par l'identifiant sous lequel les autres routes le désignent."""
    try:
        return {"patient_id": await dossier.rechercher(fhir, soignant, demande.npi)}
    except ERREURS as erreur:
        raise _http(erreur) from erreur


@routes.get("/patients/{patient_id}", responses=REFUS)
async def bandeau(
    patient_id: str, soignant: Agent = Depends(soignant_connecte), fhir: ClientFhir = Depends(client_fhir)
) -> dict[str, Any]:
    """Le bandeau patient : identité, âge, groupe sanguin, allergies, antécédents, traitements au long
    cours, cas. Sans relation de soin : ni antécédents, ni traitements, ni motif des cas d'ailleurs."""
    try:
        return await dossier.bandeau(fhir, soignant, patient_id)
    except ERREURS as erreur:
        raise _http(erreur) from erreur


@routes.get("/patients/{patient_id}/dossier", responses=REFUS)
async def lire_dossier(
    patient_id: str, soignant: Agent = Depends(soignant_connecte), fhir: ClientFhir = Depends(client_fhir)
) -> dict[str, Any]:
    """Le dossier complet, avec une relation de soin : cas, visites, mesures (et leurs séries),
    diagnostics, ordonnances."""
    try:
        return await dossier.dossier(fhir, soignant, patient_id)
    except ERREURS as erreur:
        raise _http(erreur) from erreur


@routes.post("/patients/{patient_id}/cas", status_code=status.HTTP_201_CREATED, responses=REFUS)
async def ouvrir_cas(
    patient_id: str,
    demande: modeles.NouveauCas,
    soignant: Agent = Depends(soignant_connecte),
    fhir: ClientFhir = Depends(client_fhir),
) -> dict[str, str]:
    """Ouvre un cas de visite, le patient présent : la relation de soin est établie."""
    try:
        return {"cas_id": await dossier.ouvrir_cas(fhir, soignant, patient_id, demande)}
    except ERREURS as erreur:
        raise _http(erreur) from erreur


@routes.post(
    "/cas/{cas_id}/visites",
    status_code=status.HTTP_201_CREATED,
    responses={**SAISIE, 409: {"description": "Cas clos."}},
)
async def enregistrer_visite(
    cas_id: str,
    demande: modeles.NouvelleVisite,
    soignant: Agent = Depends(soignant_connecte),
    fhir: ClientFhir = Depends(client_fhir),
) -> dict[str, str | None]:
    """Une visite, avec ses mesures, son diagnostic et son ordonnance, sous un seul numéro. Continuer
    un cas ouvert ailleurs établit la relation de soin ici. Un infirmier ne pose qu'un diagnostic provisoire."""
    try:
        visite_id, numero = await dossier.enregistrer_visite(fhir, soignant, cas_id, demande)
    except ERREURS as erreur:
        raise _http(erreur) from erreur
    return {"visite_id": visite_id, "numero_ordonnance": numero}


@routes.post("/cas/{cas_id}/cloture", responses={**REFUS, 409: {"description": "Cas déjà clos."}})
async def clore_cas(
    cas_id: str, soignant: Agent = Depends(soignant_connecte), fhir: ClientFhir = Depends(client_fhir)
) -> dict[str, str]:
    """Clôt un cas : un acte du médecin, qui a une relation de soin avec ce cas."""
    if not peut_clore(soignant.role):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "seul un médecin clôt un cas")
    try:
        await dossier.clore_cas(fhir, soignant, cas_id)
    except ERREURS as erreur:
        raise _http(erreur) from erreur
    return {"cas_id": cas_id, "statut": "termine"}


@routes.post("/patients/{patient_id}/allergies", status_code=status.HTTP_201_CREATED, responses=SAISIE)
async def declarer_allergie(
    patient_id: str,
    demande: modeles.NouvelleAllergie,
    soignant: Agent = Depends(soignant_connecte),
    fhir: ClientFhir = Depends(client_fhir),
) -> dict[str, str]:
    """Déclare une allergie, par classe ATC du catalogue des allergies : la pharmacie en arrête toute
    ligne de cette classe."""
    try:
        return {"allergie_id": await dossier.declarer_allergie(fhir, soignant, patient_id, demande)}
    except ERREURS as erreur:
        raise _http(erreur) from erreur


@routes.post("/patients/{patient_id}/antecedents", status_code=status.HTTP_201_CREATED, responses=SAISIE)
async def ajouter_antecedent(
    patient_id: str,
    demande: modeles.NouvelAntecedent,
    soignant: Agent = Depends(soignant_connecte),
    fhir: ClientFhir = Depends(client_fhir),
) -> dict[str, str]:
    """Un antécédent médical, chirurgical ou familial, avec une relation de soin."""
    try:
        return {"id": await dossier.ajouter_antecedent(fhir, soignant, patient_id, demande)}
    except ERREURS as erreur:
        raise _http(erreur) from erreur


@routes.post("/patients/{patient_id}/traitements", status_code=status.HTTP_201_CREATED, responses=SAISIE)
async def ajouter_traitement(
    patient_id: str,
    demande: modeles.NouveauTraitement,
    soignant: Agent = Depends(soignant_connecte),
    fhir: ClientFhir = Depends(client_fhir),
) -> dict[str, str]:
    """Un traitement au long cours : un produit du catalogue, ou un libellé libre."""
    try:
        return {"id": await dossier.ajouter_traitement(fhir, soignant, patient_id, demande)}
    except ERREURS as erreur:
        raise _http(erreur) from erreur


@routes.post("/traitements/{traitement_id}/arret", responses=REFUS)
async def arreter_traitement(
    traitement_id: str, soignant: Agent = Depends(soignant_connecte), fhir: ClientFhir = Depends(client_fhir)
) -> dict[str, str]:
    """Arrête un traitement au long cours."""
    try:
        await dossier.arreter_traitement(fhir, soignant, traitement_id)
    except ERREURS as erreur:
        raise _http(erreur) from erreur
    return {"id": traitement_id, "statut": "arrete"}


@routes.put("/patients/{patient_id}/groupe-sanguin", responses=SAISIE)
async def fixer_groupe_sanguin(
    patient_id: str,
    demande: modeles.GroupeSanguin,
    soignant: Agent = Depends(soignant_connecte),
    fhir: ClientFhir = Depends(client_fhir),
) -> dict[str, str]:
    """Le groupe sanguin du patient : le relevé le plus récent fait foi."""
    try:
        return {"groupe_sanguin": await dossier.fixer_groupe_sanguin(fhir, soignant, patient_id, demande)}
    except ERREURS as erreur:
        raise _http(erreur) from erreur


@routes.post("/patients/{patient_id}/acces-urgence", status_code=status.HTTP_201_CREATED, responses=REFUS)
async def acces_d_urgence(
    patient_id: str,
    demande: modeles.DemandeDUrgence,
    soignant: Agent = Depends(soignant_connecte),
    fhir: ClientFhir = Depends(client_fhir),
) -> dict[str, str]:
    """Accès d'urgence, sans relation de soin : une raison déclarée, un cas et une visite d'urgence, tracés."""
    try:
        cas_id, visite_id = await dossier.acces_d_urgence(fhir, soignant, patient_id, demande)
    except ERREURS as erreur:
        raise _http(erreur) from erreur
    return {"cas_id": cas_id, "visite_id": visite_id}


@routes.get("/patients/{patient_id}/documents", responses=REFUS)
async def documents(
    patient_id: str, soignant: Agent = Depends(soignant_connecte), fhir: ClientFhir = Depends(client_fhir)
) -> list[dict[str, Any]]:
    """Les Documents du patient, numérisés, non vérifiés : type, année, établissement d'origine,
    lisibilité, nombre de pages, origine. Avec une relation de soin."""
    try:
        return await dossier.documents(fhir, soignant, patient_id)
    except ERREURS as erreur:
        raise _http(erreur) from erreur


@routes.get("/documents/{document_id}/pages/{rang}", responses=REFUS, response_class=Response)
async def page_du_document(
    document_id: str,
    rang: int,
    soignant: Agent = Depends(soignant_connecte),
    fhir: ClientFhir = Depends(client_fhir),
) -> Response:
    """Les octets d'une page (à partir de 1), sous son format : JPEG, PNG ou PDF. Avec une relation de
    soin avec le patient du Document ; lecture tracée."""
    try:
        page = await dossier.page_du_document(fhir, soignant, document_id, rang)
    except ERREURS as erreur:
        raise _http(erreur) from erreur
    return Response(
        content=page.octets,
        media_type=page.format,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )


async def _pages_recues(fichiers: list[UploadFile]) -> list[Page]:
    """Les pages reçues, lues sans dépasser d'un octet la limite d'une page : au-delà, le 413 suit."""
    pages = []
    for fichier in fichiers:
        octets = await fichier.read(OCTETS_PAR_PAGE + 1)
        pages.append(Page(format=(fichier.content_type or "").split(";")[0].strip(), octets=octets))
    return pages


@routes.post(
    "/patients/{patient_id}/documents",
    status_code=status.HTTP_201_CREATED,
    responses={**SAISIE, 413: {"description": "Plus de 20 pages, ou une page de plus de 3 Mo."}},
)
async def ajouter_document(
    patient_id: str,
    type: Annotated[str, Form()],
    annee: Annotated[str, Form(pattern=modeles.ANNEE)],
    lisibilite: Annotated[str, Form()],
    pages: Annotated[list[UploadFile], File()],
    etablissement: Annotated[str | None, Form(max_length=200)] = None,
    soignant: Agent = Depends(soignant_connecte),
    fhir: ClientFhir = Depends(client_fhir),
) -> dict[str, Any]:
    """Un Document que le patient a apporté, numérisé pendant la visite : origine `numerisation`, auteur
    le soignant, avec une relation de soin. Multipart : `type`, `annee`, `etablissement?`, `lisibilite`, `pages`."""
    try:
        return await dossier.ajouter_document(
            fhir,
            soignant,
            patient_id,
            type_=type,
            annee=annee,
            lisibilite=lisibilite,
            etablissement=(etablissement or "").strip() or None,
            pages=await _pages_recues(pages),
        )
    except ERREURS as erreur:
        raise _http(erreur) from erreur


app = creer_service(SERVICE, routes, parle_fhir=True)
