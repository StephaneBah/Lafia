"""Service identite : ses routes sous /api/identite. Il ne parle jamais FHIR et n'est pas sur le réseau du noyau."""

from typing import Literal

from fastapi import APIRouter, FastAPI
from pydantic import BaseModel

SERVICE = "identite"


class Sante(BaseModel):
    service: str
    statut: Literal["disponible"]


PREFIXE = f"/api/{SERVICE}"

routes = APIRouter(prefix=PREFIXE)


@routes.get("/sante", response_model=Sante)
async def sante() -> Sante:
    """Le service répond. Il ne dépend pas du noyau, qu'il ne joint pas."""
    return Sante(service=SERVICE, statut="disponible")


# Le contrat OpenAPI vit sous le préfixe du service : c'est tout ce que la passerelle route vers lui.
app = FastAPI(
    title="Lafia — service identite",
    openapi_url=f"{PREFIXE}/openapi.json",
    docs_url=f"{PREFIXE}/docs",
    redoc_url=None,
)
app.include_router(routes)
