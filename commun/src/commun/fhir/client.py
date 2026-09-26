"""Client du noyau FHIR. Les services ne parlent au noyau que par lui."""

import os

import httpx

TYPE_FHIR = "application/fhir+json"
DELAI_SECONDES = 5.0


class NoyauInjoignable(Exception):
    """Le noyau n'a pas répondu, ou pas par la ressource FHIR attendue."""


class ClientFhir:
    def __init__(self, url_base: str) -> None:
        self._http = httpx.AsyncClient(
            base_url=url_base, headers={"Accept": TYPE_FHIR}, timeout=DELAI_SECONDES
        )

    @classmethod
    def depuis_environnement(cls) -> "ClientFhir":
        """Adresse du noyau lue dans `NOYAU_URL` : la même image tourne partout."""
        url_base = os.environ.get("NOYAU_URL")
        if not url_base:
            raise RuntimeError("NOYAU_URL manquante : adresse de base FHIR du noyau.")
        return cls(url_base)

    async def version_fhir(self) -> str:
        """Vérifie que le noyau répond par son CapabilityStatement (`GET metadata`) et en rend la version FHIR."""
        try:
            reponse = await self._http.get("metadata")
            reponse.raise_for_status()
            capacites = reponse.json()
        except (httpx.HTTPError, ValueError) as erreur:
            raise NoyauInjoignable(f"metadata : {erreur!r}") from erreur
        if capacites.get("resourceType") != "CapabilityStatement" or "fhirVersion" not in capacites:
            raise NoyauInjoignable("metadata : pas de CapabilityStatement avec sa version FHIR")
        version: str = capacites["fhirVersion"]
        return version

    async def fermer(self) -> None:
        await self._http.aclose()
