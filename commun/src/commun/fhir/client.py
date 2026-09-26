"""Client du noyau FHIR. Les services ne parlent au noyau que par lui."""

import os
import re
from collections.abc import Sequence
from typing import Any, TypeAlias

import httpx

TYPE_FHIR = "application/fhir+json"
DELAI_SECONDES = 5.0
# Une transaction écrit tout un lot en une fois : le noyau prend plus de temps qu'à une lecture.
DELAI_TRANSACTION_SECONDES = 120.0

# Une ressource FHIR, telle qu'elle circule en JSON.
Ressource: TypeAlias = dict[str, Any]


class NoyauInjoignable(Exception):
    """Le noyau n'a pas répondu, ou pas par la ressource FHIR attendue."""


class TransactionRefusee(Exception):
    """Le noyau a répondu, et refusé la transaction : rien n'en a été écrit."""


def mise_a_jour(ressource: Ressource) -> Ressource:
    """L'entrée de transaction qui écrit `ressource` sous son identifiant : créée, ou mise à jour.

    Le noyau ne donne pas de nouvelle version à une ressource dont le contenu n'a pas changé.
    """
    return {
        "resource": ressource,
        "request": {"method": "PUT", "url": f"{ressource['resourceType']}/{ressource['id']}"},
    }


def _codes_d_erreur(reponse: httpx.Response) -> str:
    """Les codes d'erreur du noyau (`HAPI-0450`) dans son OperationOutcome : jamais son message, qui
    peut citer le contenu d'une ressource."""
    return ", ".join(sorted(set(re.findall(r"HAPI-\d+", reponse.text)))) or "sans code"


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

    async def transaction(self, entrees: Sequence[Ressource]) -> list[Ressource]:
        """Envoie `entrees` au noyau en une transaction FHIR : toutes écrites, ou aucune.

        Rend la réponse du noyau à chaque entrée, dans l'ordre des entrées (`response.status`,
        `response.etag`, …). `TransactionRefusee` quand le noyau la refuse, `NoyauInjoignable` quand
        il ne répond pas.
        """
        lot = {"resourceType": "Bundle", "type": "transaction", "entry": list(entrees)}
        try:
            reponse = await self._http.post(
                "", json=lot, headers={"Content-Type": TYPE_FHIR}, timeout=DELAI_TRANSACTION_SECONDES
            )
        except httpx.HTTPError as erreur:
            raise NoyauInjoignable(f"transaction : {erreur!r}") from erreur
        if reponse.is_error:
            raise TransactionRefusee(f"transaction : {reponse.status_code}, {_codes_d_erreur(reponse)}")
        try:
            resultat = reponse.json()
        except ValueError as erreur:
            raise NoyauInjoignable("transaction : réponse illisible") from erreur
        if resultat.get("resourceType") != "Bundle" or len(resultat.get("entry", [])) != len(lot["entry"]):
            raise NoyauInjoignable("transaction : pas de Bundle de réponse, entrée par entrée")
        reponses: list[Ressource] = resultat["entry"]
        return reponses

    async def fermer(self) -> None:
        await self._http.aclose()
