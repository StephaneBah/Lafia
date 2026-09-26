"""Service pharmacie : ses routes sous /api/pharmacie. /sante et le client du noyau viennent de `commun`."""

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, Field

from commun.fhir.client import ClientFhir
from commun.jeton import Agent, Officine, Role, VerificateurDeJetons
from commun.service import client_fhir, creer_service
from pharmacie import officine as en_officine
from pharmacie import ordonnance
from pharmacie.regles.acces import ROLES_ADMIS
from pharmacie.regles.delivrance import DelivranceRefusee

SERVICE = "pharmacie"

# La clé publique est lue au démarrage : sans elle, le service ne démarre pas.
jetons = VerificateurDeJetons.depuis_environnement()
pharmacien_ou_officine_connecte = jetons.agent_ou_officine(ROLES_ADMIS)
# Le comptoir d'un établissement : le pharmacien seul. L'officine a ses propres routes.
pharmacien_connecte = jetons.agent({Role.PHARMACIEN})
_officine_ou_agent = jetons.agent_ou_officine({Role.OFFICINE})


def officine_connectee(porteur: Agent | Officine = Depends(_officine_ou_agent)) -> Officine:
    """L'officine du jeton ; tout autre porteur est refusé (403)."""
    if not isinstance(porteur, Officine):
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="rôle non admis")
    return porteur

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


REFUS: dict[int | str, dict[str, str]] = {
    401: {"description": "Jeton absent, mal formé, expiré ou mal signé."},
    403: {"description": "Rôle autre que pharmacien, ou ordonnance à servir dans un autre établissement."},
    404: {"description": "Aucune ligne à remettre ne porte ce numéro."},
}
NUMERO = Path(description="Numéro d'ordonnance, `ORD-7K4-M2P` ; la saisie est normalisée.", max_length=32)


def _refus_de_lecture(erreur: Exception) -> HTTPException:
    if isinstance(erreur, ordonnance.AutreEtablissement):
        return HTTPException(status.HTTP_403_FORBIDDEN, detail="ordonnance à servir dans un autre établissement")
    return HTTPException(status.HTTP_404_NOT_FOUND, detail="aucune ordonnance à remettre sous ce numéro")


@routes.get("/ordonnances/{numero}", responses=REFUS)
async def consulter_ordonnance(
    numero: str = NUMERO,
    pharmacien: Agent = Depends(pharmacien_connecte),
    fhir: ClientFhir = Depends(client_fhir),
) -> ordonnance.OrdonnanceVue:
    """L'ordonnance au comptoir : les lignes à remettre, payées ou non, ce qui en reste, et les
    allergies du patient qui concernent une ligne. L'accès est tracé."""
    try:
        return await ordonnance.consulter(fhir, numero, pharmacien)
    except (ordonnance.Introuvable, ordonnance.AutreEtablissement) as erreur:
        raise _refus_de_lecture(erreur) from None


class LigneDemandee(BaseModel):
    id: str = Field(max_length=64)
    quantite: int


class DemandeDeDelivrance(BaseModel):
    lignes: list[LigneDemandee] = Field(max_length=50)
    allergie_reconnue: bool = False


@routes.post(
    "/ordonnances/{numero}/delivrances",
    status_code=status.HTTP_201_CREATED,
    responses={
        **REFUS,
        409: {"description": "Ligne non payée, quantité au-delà du reste, ou allergie non reconnue."},
    },
)
async def delivrer(
    demande: DemandeDeDelivrance,
    numero: str = NUMERO,
    pharmacien: Agent = Depends(pharmacien_connecte),
    fhir: ClientFhir = Depends(client_fhir),
) -> ordonnance.Delivrances:
    """Remet les lignes demandées, en partie si besoin : une délivrance par ligne. Une ligne que
    concerne une allergie du patient ne se remet qu'avec `allergie_reconnue`."""
    try:
        return await ordonnance.delivrer(
            fhir, numero, pharmacien, [(l.id, l.quantite) for l in demande.lignes], demande.allergie_reconnue
        )
    except (ordonnance.Introuvable, ordonnance.AutreEtablissement) as erreur:
        raise _refus_de_lecture(erreur) from None
    except DelivranceRefusee as refus:
        raise HTTPException(refus.statut, detail=refus.detail) from None


REFUS_OFFICINE: dict[int | str, dict[str, str]] = {
    401: {"description": "Jeton absent, mal formé, expiré ou mal signé."},
    403: {"description": "Rôle autre qu'officine."},
    404: {"description": "Aucun médicament ne porte ce numéro d'ordonnance."},
}


def _introuvable() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, detail="aucune ordonnance sous ce numéro")


@routes.get("/officine/ordonnances/{numero}", responses=REFUS_OFFICINE)
async def verifier_en_officine(
    numero: str = NUMERO,
    officine: Officine = Depends(officine_connectee),
    fhir: ClientFhir = Depends(client_fhir),
) -> en_officine.OrdonnanceEnOfficine:
    """L'ordonnance vue d'une officine : prescripteur, date et établissement pour la vérifier, et
    chaque médicament avec ce qui en reste et s'il peut s'y vendre. Jamais le patient. L'accès est tracé."""
    try:
        return await en_officine.consulter(fhir, numero, officine)
    except ordonnance.Introuvable:
        raise _introuvable() from None


class DemandeDeVente(BaseModel):
    lignes: list[LigneDemandee] = Field(max_length=50)


@routes.post(
    "/officine/ordonnances/{numero}/ventes",
    status_code=status.HTTP_201_CREATED,
    responses={
        **REFUS_OFFICINE,
        409: {"description": "Ligne payée à la caisse d'un établissement, ou quantité au-delà du reste."},
        422: {"description": "Aucune ligne, ligne déclarée deux fois, ou quantité nulle."},
    },
)
async def declarer_une_vente(
    demande: DemandeDeVente,
    numero: str = NUMERO,
    officine: Officine = Depends(officine_connectee),
    fhir: ClientFhir = Depends(client_fhir),
) -> ordonnance.Delivrances:
    """Déclare les lignes que l'officine a vendues, en partie si besoin : une délivrance par ligne."""
    try:
        return await en_officine.vendre(fhir, numero, officine, [(l.id, l.quantite) for l in demande.lignes])
    except ordonnance.Introuvable:
        raise _introuvable() from None
    except DelivranceRefusee as refus:
        raise HTTPException(refus.statut, detail=refus.detail) from None


app = creer_service(SERVICE, routes, parle_fhir=True)
