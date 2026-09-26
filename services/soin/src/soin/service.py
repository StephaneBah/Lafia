"""Service soin : ses routes sous /api/soin. /sante et le client du noyau viennent de `commun`.

Les routes traduisent HTTP : le travail est dans `soin.dossier`, les règles dans `soin.regles`.
"""

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, StringConstraints

from commun.fhir.client import ClientFhir
from commun.jeton import Agent, VerificateurDeJetons
from commun.service import client_fhir, creer_service
from soin import dossier
from soin.regles.acces import ROLES_ADMIS
from soin.regles.visite import VisiteRefusee, peut_clore

SERVICE = "soin"

# La clé publique est lue au démarrage : sans elle, le service ne démarre pas.
jetons = VerificateurDeJetons.depuis_environnement()
soignant_connecte = jetons.agent(ROLES_ADMIS)

routes = APIRouter()

Npi = Annotated[str, StringConstraints(pattern=r"^\d{13}$")]
Texte = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]

REFUS = {
    401: {"description": "Jeton absent, mal formé, expiré ou mal signé."},
    403: {"description": "Rôle que le service soin ne sert pas, ou pas de relation de soin."},
    404: {"description": "Aucun patient pour ce NPI, ou aucun cas sous cet identifiant."},
}


def _http(erreur: Exception) -> HTTPException:
    match erreur:
        case dossier.PatientInconnu():
            return HTTPException(status.HTTP_404_NOT_FOUND, "aucun patient pour ce NPI")
        case dossier.CasInconnu():
            return HTTPException(status.HTTP_404_NOT_FOUND, "aucun cas sous cet identifiant")
        case dossier.SansRelationDeSoin():
            return HTTPException(status.HTTP_403_FORBIDDEN, "pas de relation de soin avec ce patient")
        case dossier.CasClos():
            return HTTPException(status.HTTP_409_CONFLICT, "ce cas est clos")
        case VisiteRefusee():
            return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(erreur))
    raise erreur


ERREURS = (dossier.PatientInconnu, dossier.CasInconnu, dossier.SansRelationDeSoin, dossier.CasClos, VisiteRefusee)


@routes.get("/session", responses=REFUS)
async def session(soignant: Agent = Depends(soignant_connecte)) -> Agent:
    """Le soignant connecté : son identifiant, son rôle et son établissement, lus de son jeton vérifié."""
    return soignant


@routes.get("/catalogue", responses=REFUS)
async def catalogue(
    soignant: Agent = Depends(soignant_connecte), fhir: ClientFhir = Depends(client_fhir)
) -> dict[str, Any]:
    """Ce qu'une visite peut porter : produits tarifés à l'établissement, mesures, diagnostics."""
    return await dossier.catalogue(fhir, soignant.etablissement)


@routes.get("/patients/{npi}", responses=REFUS)
async def patient(
    npi: Npi, soignant: Agent = Depends(soignant_connecte), fhir: ClientFhir = Depends(client_fhir)
) -> dict[str, Any]:
    """La fiche d'un patient trouvé par NPI : identité, allergies, titres des cas, relation de soin. Rien de clinique."""
    try:
        return await dossier.fiche(fhir, soignant, npi)
    except ERREURS as erreur:
        raise _http(erreur) from erreur


@routes.get("/patients/{npi}/dossier", responses=REFUS)
async def lire_dossier(
    npi: Npi, soignant: Agent = Depends(soignant_connecte), fhir: ClientFhir = Depends(client_fhir)
) -> dict[str, Any]:
    """Le dossier complet, avec une relation de soin : cas, visites, mesures, diagnostics, ordonnances."""
    try:
        return await dossier.dossier(fhir, soignant, npi)
    except ERREURS as erreur:
        raise _http(erreur) from erreur


class NouveauCas(BaseModel):
    motif: Texte


@routes.post("/patients/{npi}/cas", status_code=status.HTTP_201_CREATED, responses=REFUS)
async def ouvrir_cas(
    npi: Npi, demande: NouveauCas, soignant: Agent = Depends(soignant_connecte), fhir: ClientFhir = Depends(client_fhir)
) -> dict[str, str]:
    """Ouvre un cas de visite, le patient présent : la relation de soin est établie."""
    try:
        return {"cas_id": await dossier.ouvrir_cas(fhir, soignant, npi, demande.motif)}
    except ERREURS as erreur:
        raise _http(erreur) from erreur


class MesureSaisie(BaseModel):
    code: str
    valeur: float | str
    valeur2: float | None = None


class DiagnosticSaisi(BaseModel):
    code: str
    confirme: bool = False
    note: Annotated[str, StringConstraints(max_length=1000)] | None = None


MomentDePrise = Literal["matin", "midi", "soir", "nuit"]


class LigneSaisie(BaseModel):
    produit: str
    quantite: int = Field(ge=1)
    dose: float = Field(gt=0, default=1)
    moments: list[MomentDePrise] = []
    jours: int = Field(ge=1, default=1)


class NouvelleVisite(BaseModel):
    type: Literal["consultation", "soins-infirmiers", "continuite"]
    motif: Texte
    mesures: list[MesureSaisie] = []
    diagnostic: DiagnosticSaisi | None = None
    ordonnance: list[LigneSaisie] | None = None


@routes.post(
    "/cas/{cas_id}/visites",
    status_code=status.HTTP_201_CREATED,
    responses={**REFUS, 409: {"description": "Cas clos."}, 422: {"description": "Hors catalogue."}},
)
async def enregistrer_visite(
    cas_id: str, demande: NouvelleVisite, soignant: Agent = Depends(soignant_connecte), fhir: ClientFhir = Depends(client_fhir)
) -> dict[str, str | None]:
    """Une visite, avec ses mesures, son diagnostic et son ordonnance, sous un seul numéro. Continuer
    un cas ouvert ailleurs établit la relation de soin ici. Un infirmier ne pose qu'un diagnostic provisoire."""
    diagnostic = demande.diagnostic
    try:
        visite_id, numero = await dossier.enregistrer_visite(
            fhir,
            soignant,
            cas_id,
            type_=demande.type,
            motif=demande.motif,
            mesures=[(m.code, m.valeur, m.valeur2) for m in demande.mesures],
            diagnostic=(diagnostic.code, diagnostic.confirme, diagnostic.note or None) if diagnostic else None,
            ordonnance=[(l.produit, l.quantite, l.dose, list(l.moments), l.jours) for l in demande.ordonnance or []],
        )
    except ERREURS as erreur:
        raise _http(erreur) from erreur
    return {"visite_id": visite_id, "numero_ordonnance": numero}


@routes.post("/cas/{cas_id}/cloture", responses={**REFUS, 409: {"description": "Cas déjà clos."}})
async def clore_cas(
    cas_id: str, soignant: Agent = Depends(soignant_connecte), fhir: ClientFhir = Depends(client_fhir)
) -> dict[str, str]:
    """Clôt un cas : un acte du médecin."""
    if not peut_clore(soignant.role):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "seul un médecin clôt un cas")
    try:
        await dossier.clore_cas(fhir, soignant, cas_id)
    except ERREURS as erreur:
        raise _http(erreur) from erreur
    return {"cas_id": cas_id, "statut": "termine"}


class NouvelleAllergie(BaseModel):
    code_atc: Annotated[str, StringConstraints(pattern=r"^[A-Z][0-9]{2}[A-Z0-9]{0,4}$")]
    libelle: Texte


@routes.post("/patients/{npi}/allergies", status_code=status.HTTP_201_CREATED, responses=REFUS)
async def declarer_allergie(
    npi: Npi, demande: NouvelleAllergie, soignant: Agent = Depends(soignant_connecte), fhir: ClientFhir = Depends(client_fhir)
) -> dict[str, str]:
    """Déclare une allergie, par classe ATC : la pharmacie en arrête toute ligne de cette classe."""
    try:
        return {"allergie_id": await dossier.declarer_allergie(fhir, soignant, npi, demande.code_atc, demande.libelle)}
    except ERREURS as erreur:
        raise _http(erreur) from erreur


class DemandeDUrgence(BaseModel):
    raison: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=500)]


@routes.post("/patients/{npi}/acces-urgence", status_code=status.HTTP_201_CREATED, responses=REFUS)
async def acces_d_urgence(
    npi: Npi, demande: DemandeDUrgence, soignant: Agent = Depends(soignant_connecte), fhir: ClientFhir = Depends(client_fhir)
) -> dict[str, str]:
    """Accès d'urgence, sans relation de soin : une raison déclarée, un cas et une visite d'urgence, tracés."""
    try:
        cas_id, visite_id = await dossier.acces_d_urgence(fhir, soignant, npi, demande.raison)
    except ERREURS as erreur:
        raise _http(erreur) from erreur
    return {"cas_id": cas_id, "visite_id": visite_id}


app = creer_service(SERVICE, routes, parle_fhir=True)
