"""Squelette d'un service : son app FastAPI, sa route /sante, son contrat OpenAPI.

Un service ne tient que ses propres routes ; `creer_service()` les place, avec /sante, sous
/api/<service>. Un service qui parle FHIR joint le noyau par le client que `client_fhir` lui donne.
"""

import logging
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import Literal

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from commun.fhir.client import ClientFhir, NoyauInjoignable


class EtatNoyau(BaseModel):
    statut: Literal["disponible", "injoignable"]
    version_fhir: str | None = None


class Sante(BaseModel):
    """État d'un service qui parle FHIR, et du noyau derrière lui."""

    service: str
    statut: Literal["disponible", "indisponible"]
    noyau: EtatNoyau


class SanteSansNoyau(BaseModel):
    """État d'un service qui ne joint pas le noyau : il répond, ou pas du tout."""

    service: str
    statut: Literal["disponible"]


@asynccontextmanager
async def _cycle_de_vie_fhir(app: FastAPI) -> AsyncIterator[None]:
    app.state.fhir = ClientFhir.depuis_environnement()
    yield
    await app.state.fhir.fermer()


def client_fhir(request: Request) -> ClientFhir:
    """Dépendance FastAPI : le client du noyau, ouvert au démarrage d'un service qui parle FHIR."""
    fhir: ClientFhir = request.app.state.fhir
    return fhir


def _sante_avec_noyau(service: str) -> APIRouter:
    journal = logging.getLogger(service)
    routes = APIRouter()

    @routes.get("/sante", response_model=Sante, responses={503: {"model": Sante}})
    async def sante(fhir: ClientFhir = Depends(client_fhir)) -> Sante | JSONResponse:
        """Le service répond et joint le noyau, dont il rapporte la version FHIR."""
        try:
            version_fhir = await fhir.version_fhir()
        except NoyauInjoignable as erreur:
            journal.warning("noyau injoignable : %s", erreur)
            indisponible = Sante(
                service=service, statut="indisponible", noyau=EtatNoyau(statut="injoignable")
            )
            return JSONResponse(status_code=503, content=indisponible.model_dump())
        return Sante(
            service=service,
            statut="disponible",
            noyau=EtatNoyau(statut="disponible", version_fhir=version_fhir),
        )

    return routes


def _sante_sans_noyau(service: str) -> APIRouter:
    routes = APIRouter()

    @routes.get("/sante", response_model=SanteSansNoyau)
    async def sante() -> SanteSansNoyau:
        """Le service répond. Il ne joint pas le noyau."""
        return SanteSansNoyau(service=service, statut="disponible")

    return routes


def creer_service(
    service: str,
    *routes: APIRouter,
    parle_fhir: bool,
    cycle_de_vie: Callable[[FastAPI], AbstractAsyncContextManager[None]] | None = None,
) -> FastAPI:
    """Le service en app FastAPI : /sante et ses `routes`, sous /api/<service>.

    Le contrat OpenAPI et sa documentation vivent sous le même préfixe : c'est tout ce que la
    passerelle route vers le service. Un service qui parle FHIR ouvre le client du noyau au démarrage,
    et sa /sante joint le noyau (503 quand il ne répond pas) ; les autres ne rapportent que leur état,
    et ouvrent au démarrage ce dont ils ont besoin par leur propre `cycle_de_vie`.
    """
    if parle_fhir and cycle_de_vie:
        raise ValueError("un service qui parle FHIR a le cycle de vie du client du noyau")
    prefixe = f"/api/{service}"
    app = FastAPI(
        title=f"Lafia — service {service}",
        lifespan=_cycle_de_vie_fhir if parle_fhir else cycle_de_vie,
        openapi_url=f"{prefixe}/openapi.json",
        docs_url=f"{prefixe}/docs",
        redoc_url=None,
    )
    sante = _sante_avec_noyau(service) if parle_fhir else _sante_sans_noyau(service)
    for routeur in (sante, *routes):
        app.include_router(routeur, prefix=prefixe)
    return app
