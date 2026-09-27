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
# Une entrée de transaction : une ressource, et la requête qui l'écrit.
Entree: TypeAlias = dict[str, Any]


class NoyauInjoignable(Exception):
    """Le noyau n'a pas répondu, ou pas par la ressource FHIR attendue."""


class TransactionRefusee(Exception):
    """Le noyau a répondu, et refusé la transaction : rien n'en a été écrit."""


def ecriture(ressource: Ressource) -> Entree:
    """L'entrée de transaction qui écrit `ressource` sous son identifiant : créée, ou mise à jour.

    Le noyau ne donne pas de nouvelle version à une ressource dont le contenu n'a pas changé.
    """
    return {
        "resource": ressource,
        "request": {"method": "PUT", "url": f"{ressource['resourceType']}/{ressource['id']}"},
    }


def ecriture_si_inchangee(ressource: Ressource, lue: Ressource) -> Entree:
    """L'entrée qui écrit la nouvelle version de `lue`, si personne ne l'a changée depuis sa lecture
    (`If-Match` sur sa version) : sinon le noyau refuse la transaction entière."""
    entree = ecriture(ressource)
    entree["request"]["ifMatch"] = f'W/"{lue.get("meta", {}).get("versionId", "1")}"'
    return entree


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

    async def transaction(self, entrees: Sequence[Entree]) -> list[int]:
        """Envoie `entrees` au noyau en une transaction FHIR : toutes écrites, ou aucune.

        Rend le statut HTTP de chaque entrée, dans leur ordre : 201 pour une ressource créée, 200 pour
        une ressource mise à jour ou laissée telle quelle. `TransactionRefusee` quand le noyau la
        refuse, `NoyauInjoignable` quand il ne répond pas.
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
        # Le statut d'une entrée commence par son code : "201 Created".
        return [int(reponse["response"]["status"].split()[0]) for reponse in resultat["entry"]]

    async def lire(self, type_: str, id_: str) -> Ressource | None:
        """La ressource `type_/id_`, ou None quand le noyau ne la connaît pas."""
        try:
            reponse = await self._http.get(f"{type_}/{id_}")
        except httpx.HTTPError as erreur:
            raise NoyauInjoignable(f"lecture {type_} : {erreur!r}") from erreur
        if reponse.status_code in (404, 410):
            return None
        if reponse.is_error:
            raise NoyauInjoignable(f"lecture {type_} : {reponse.status_code}, {_codes_d_erreur(reponse)}")
        ressource: Ressource = reponse.json()
        return ressource

    async def chercher(self, type_: str, parametres: dict[str, str] | Sequence[tuple[str, str]]) -> list[Ressource]:
        """Les ressources `type_` qui répondent à `parametres` (recherche FHIR), toutes pages suivies.

        Les ressources incluses (`_include`, `_revinclude`) viennent avec, à la suite.
        """
        params = list(parametres.items()) if isinstance(parametres, dict) else list(parametres)
        if not any(nom == "_count" for nom, _ in params):
            params.append(("_count", "200"))
        ressources: list[Ressource] = []
        url: str | None = type_
        requete_params: list[tuple[str, str]] | None = params
        while url:
            try:
                # Sans ce cache refusé, le noyau resert pendant une minute le résultat d'une même
                # recherche : un cas qu'on vient d'ouvrir n'y serait pas encore.
                reponse = await self._http.get(url, params=requete_params, headers={"Cache-Control": "no-cache"})
            except httpx.HTTPError as erreur:
                raise NoyauInjoignable(f"recherche {type_} : {erreur!r}") from erreur
            if reponse.is_error:
                raise NoyauInjoignable(f"recherche {type_} : {reponse.status_code}, {_codes_d_erreur(reponse)}")
            lot = reponse.json()
            ressources.extend(entree["resource"] for entree in lot.get("entry", []))
            url = next((lien["url"] for lien in lot.get("link", []) if lien.get("relation") == "next"), None)
            requete_params = None
        return ressources

    async def creer(self, ressource: Ressource) -> Ressource:
        """Crée `ressource` (POST) et la rend telle que le noyau l'a écrite, avec son identifiant."""
        return await self._ecrire("POST", ressource["resourceType"], ressource)

    async def mettre_a_jour(self, ressource: Ressource) -> Ressource:
        """Écrit une nouvelle version de `ressource` (PUT) : l'ancienne reste dans son historique."""
        return await self._ecrire("PUT", f"{ressource['resourceType']}/{ressource['id']}", ressource)

    async def _ecrire(self, methode: str, url: str, ressource: Ressource) -> Ressource:
        try:
            reponse = await self._http.request(
                methode, url, json=ressource, headers={"Content-Type": TYPE_FHIR, "Prefer": "return=representation"}
            )
        except httpx.HTTPError as erreur:
            raise NoyauInjoignable(f"écriture {url} : {erreur!r}") from erreur
        if reponse.is_error:
            raise TransactionRefusee(f"écriture {ressource['resourceType']} : {reponse.status_code}, {_codes_d_erreur(reponse)}")
        ecrite: Ressource = reponse.json()
        return ecrite

    async def fermer(self) -> None:
        await self._http.aclose()
