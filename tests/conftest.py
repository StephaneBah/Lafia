"""Suite boîte noire : elle observe la pile en marche du dehors, comme un usager ou un attaquant.

Chaque application est jointe par son sous-domaine, `<application>.<domaine>`.
La même suite vise la pile locale ou l'adresse publique selon l'environnement :

- `LAFIA_DOMAINE` : domaine de base, `localhost` par défaut.
- `LAFIA_ADRESSE` : adresse IP où joindre la passerelle. Par défaut `127.0.0.1` pour
  `localhost` (tous les systèmes ne résolvent pas `*.localhost`), le DNS sinon.

Les certificats sont vérifiés : en local contre l'autorité interne de Caddy, lue dans le
conteneur de la passerelle ; ailleurs contre les autorités publiques.

Tout passe par la passerelle, sauf l'isolement réseau, qui ne s'y observe pas : ces vérifications
passent par `docker`, sur la machine de la pile visée, et sont sautées quand elle tourne ailleurs.
"""

import os
import ssl
import subprocess
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest

RACINE_DU_DEPOT = Path(__file__).resolve().parent.parent
RACINE_CA_CADDY = "/data/caddy/pki/authorities/local/root.crt"

DOMAINE = os.environ.get("LAFIA_DOMAINE", "localhost")
LOCAL = DOMAINE == "localhost"
ADRESSE = os.environ.get("LAFIA_ADRESSE") or ("127.0.0.1" if LOCAL else None)


class _VersAdresse(httpx.HTTPTransport):
    """Joint la passerelle à une adresse fixe, en gardant le sous-domaine pour Host et SNI."""

    def __init__(self, adresse: str, **options: Any) -> None:
        super().__init__(**options)
        self._adresse = adresse

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        request.extensions["sni_hostname"] = request.url.host
        request.url = request.url.copy_with(host=self._adresse)
        return super().handle_request(request)


def _docker(*arguments: str) -> subprocess.CompletedProcess[str]:
    """La commande `docker`, lancée depuis la racine du dépôt, où `docker compose` trouve la pile."""
    return subprocess.run(
        ["docker", *arguments], cwd=RACINE_DU_DEPOT, capture_output=True, text=True
    )


def _pile_locale_absente(detail: str) -> None:
    pytest.exit(
        f"Pile locale injoignable : la lancer avec `docker compose up -d --build --wait`.\n{detail}",
        returncode=1,
    )


def _contexte_tls() -> ssl.SSLContext:
    if not LOCAL:
        return ssl.create_default_context()
    racine_ca = _docker("compose", "exec", "-T", "passerelle", "cat", RACINE_CA_CADDY)
    if racine_ca.returncode != 0:
        _pile_locale_absente(racine_ca.stderr)
    return ssl.create_default_context(cadata=racine_ca.stdout)


def _domaine_servi_ici() -> str | None:
    """Le domaine que sert la passerelle de cette machine ; `None` quand aucune n'y tourne."""
    try:
        domaine = _docker("compose", "exec", "-T", "passerelle", "printenv", "LAFIA_DOMAINE")
    except FileNotFoundError:
        return None
    return domaine.stdout.strip() if domaine.returncode == 0 else None


@pytest.fixture(scope="session")
def docker() -> Callable[..., subprocess.CompletedProcess[str]]:
    """`docker` sur la pile de cette machine : `docker("compose", "ps")`.

    Seulement quand cette pile est celle que la suite vise, c'est-à-dire quand sa passerelle sert
    `LAFIA_DOMAINE` : sinon ses conteneurs ne diraient rien de la pile visée, et le test est sauté.
    En local, la pile est exigée.
    """
    domaine_servi_ici = _domaine_servi_ici()
    if domaine_servi_ici != DOMAINE:
        if LOCAL:
            _pile_locale_absente(f"domaine servi par cette machine : {domaine_servi_ici}")
        pytest.skip(f"la pile qui sert {DOMAINE} ne tourne pas sur cette machine")
    return _docker


@pytest.fixture(scope="session")
def application() -> Iterator[Callable[[str], httpx.Client]]:
    """Client HTTP d'une application, adressée par son sous-domaine sur la passerelle.

    Un client par application : chaque sous-domaine garde ses propres connexions TLS.
    """
    contexte = _contexte_tls()
    clients: dict[str, httpx.Client] = {}

    def client_de(nom: str) -> httpx.Client:
        if nom not in clients:
            transport = (
                _VersAdresse(ADRESSE, verify=contexte)
                if ADRESSE
                else httpx.HTTPTransport(verify=contexte)
            )
            clients[nom] = httpx.Client(
                base_url=f"https://{nom}.{DOMAINE}", transport=transport, timeout=10
            )
        return clients[nom]

    yield client_de
    for client in clients.values():
        client.close()
