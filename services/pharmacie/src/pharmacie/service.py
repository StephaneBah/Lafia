"""Service pharmacie : ses routes sous /api/pharmacie. /sante et le client du noyau viennent de `commun`."""

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, Field

from commun.fhir.client import ClientFhir
from commun.jeton import Agent, Officine, Role, VerificateurDeJetons
from commun.service import client_fhir, creer_service
from pharmacie import ordonnance
from pharmacie.regles.acces import ROLES_ADMIS
from pharmacie.regles.delivrance import DelivranceRefusee

SERVICE = "pharmacie"

# La clé publique est lue au démarrage : sans elle, le service ne démarre pas.
jetons = VerificateurDeJetons.depuis_environnement()
pharmacien_ou_officine_connecte = jetons.agent_ou_officine(ROLES_ADMIS)
# Le comptoir d'un établissement : le pharmacien seul. L'officine (F3.7) n'y a pas accès.
pharmacien_connecte = jetons.agent({Role.PHARMACIEN})

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


app = creer_service(SERVICE, routes, parle_fhir=True)
