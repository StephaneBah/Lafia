"""Service soin : ses routes sous /api/soin, le noyau joint par le client FHIR de `commun`."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from commun.fhir import ClientFhir, NoyauInjoignable

SERVICE = "soin"

journal = logging.getLogger(SERVICE)


class EtatNoyau(BaseModel):
    statut: Literal["disponible", "injoignable"]
    version_fhir: str | None = None


class Sante(BaseModel):
    service: str
    statut: Literal["disponible", "indisponible"]
    noyau: EtatNoyau


@asynccontextmanager
async def cycle_de_vie(app: FastAPI) -> AsyncIterator[None]:
    app.state.fhir = ClientFhir.depuis_environnement()
    yield
    await app.state.fhir.fermer()


def client_fhir(request: Request) -> ClientFhir:
    fhir: ClientFhir = request.app.state.fhir
    return fhir


PREFIXE = f"/api/{SERVICE}"

routes = APIRouter(prefix=PREFIXE)


@routes.get("/sante", response_model=Sante, responses={503: {"model": Sante}})
async def sante(fhir: ClientFhir = Depends(client_fhir)) -> Sante | JSONResponse:
    """Le service répond et joint le noyau, dont il rapporte la version FHIR."""
    try:
        version_fhir = await fhir.version_fhir()
    except NoyauInjoignable as erreur:
        journal.warning("noyau injoignable : %s", erreur)
        indisponible = Sante(
            service=SERVICE, statut="indisponible", noyau=EtatNoyau(statut="injoignable")
        )
        return JSONResponse(status_code=503, content=indisponible.model_dump())
    return Sante(
        service=SERVICE,
        statut="disponible",
        noyau=EtatNoyau(statut="disponible", version_fhir=version_fhir),
    )


# Le contrat OpenAPI vit sous le préfixe du service : c'est tout ce que la passerelle route vers lui.
app = FastAPI(
    title="Lafia — service soin",
    lifespan=cycle_de_vie,
    openapi_url=f"{PREFIXE}/openapi.json",
    docs_url=f"{PREFIXE}/docs",
    redoc_url=None,
)
app.include_router(routes)
