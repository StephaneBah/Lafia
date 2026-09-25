"""Suite boîte noire : elle parle à la pile en marche par la passerelle, et rien d'autre.

Chaque application est jointe par son sous-domaine, `<application>.<domaine>`.
La même suite vise la pile locale ou l'adresse publique selon l'environnement :

- `LAFIA_DOMAINE` : domaine de base, `localhost` par défaut.
- `LAFIA_ADRESSE` : adresse IP où joindre la passerelle. Par défaut `127.0.0.1` pour
  `localhost` (tous les systèmes ne résolvent pas `*.localhost`), le DNS sinon.

Les certificats sont vérifiés : en local contre l'autorité interne de Caddy, lue dans le
conteneur de la passerelle ; ailleurs contre les autorités publiques.
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


def _contexte_tls() -> ssl.SSLContext:
    if not LOCAL:
        return ssl.create_default_context()
    racine_ca = subprocess.run(
        ["docker", "compose", "exec", "-T", "passerelle", "cat", RACINE_CA_CADDY],
        cwd=RACINE_DU_DEPOT,
        capture_output=True,
        text=True,
    )
    if racine_ca.returncode != 0:
        pytest.exit(
            "Passerelle locale injoignable : lancer la pile avec "
            f"`docker compose up -d --build --wait`.\n{racine_ca.stderr}",
            returncode=1,
        )
    return ssl.create_default_context(cadata=racine_ca.stdout)


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
