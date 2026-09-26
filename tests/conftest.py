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

Les jetons de test sont signés de la clé privée donnée par `JETON_CLE_PRIVEE`, celle dont la pile
visée connaît la clé publique. En local, sans elle, la clé de développement, que seule une pile
servie sur localhost accepte ; ailleurs, sans elle, les tests qui en ont besoin sont sautés.
"""

import base64
import os
import ssl
import subprocess
from collections.abc import Callable, Iterator
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import load_der_private_key

RACINE_DU_DEPOT = Path(__file__).resolve().parent.parent
RACINE_CA_CADDY = "/data/caddy/pki/authorities/local/root.crt"

DOMAINE = os.environ.get("LAFIA_DOMAINE", "localhost")
LOCAL = DOMAINE == "localhost"
ADRESSE = os.environ.get("LAFIA_ADRESSE") or ("127.0.0.1" if LOCAL else None)

# Clé privée de la paire de développement. Elle n'a rien de secret : une pile servie sur localhost,
# sans JETON_CLE_PUBLIQUE, accepte les jetons qu'elle signe ; toute autre pile refuse sa clé publique
# (commun/src/commun/jeton.py).
CLE_PRIVEE_DE_DEVELOPPEMENT = "MC4CAQAwBQYDK2VwBCIEINp8yVHhQe5B/gcbA5wNMNwe0d+oaAY7090L95AC8EvZ"

# Revendications d'un jeton de test, par rôle : identifiants synthétiques seulement.
REVENDICATIONS_AGENT = {"sub": "agent-test-1", "etablissement": "etablissement-test-1"}
REVENDICATIONS_CITOYEN = {"sub": "citoyen-test-1", "npi": "0000000001"}


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


@pytest.fixture(scope="session")
def signer_jeton() -> Callable[..., str]:
    """Signe un jeton que la pile visée accepte : `signer_jeton("médecin")`.

    Les revendications par défaut du rôle se remplacent par mot-clé ; `None` en retire une.
    `expire_dans` règle l'expiration ; `cle` signe d'une autre clé que celle de la pile visée.
    """
    cle_en_base64 = os.environ.get("JETON_CLE_PRIVEE") or (CLE_PRIVEE_DE_DEVELOPPEMENT if LOCAL else None)
    if cle_en_base64 is None:
        pytest.skip(f"JETON_CLE_PRIVEE absente : pas de jeton accepté par la pile qui sert {DOMAINE}")
    cle_de_la_pile = load_der_private_key(base64.b64decode(cle_en_base64), password=None)
    assert isinstance(cle_de_la_pile, Ed25519PrivateKey), "JETON_CLE_PRIVEE : une clé privée Ed25519"

    def signer(
        role: str,
        *,
        cle: Ed25519PrivateKey = cle_de_la_pile,
        expire_dans: timedelta = timedelta(minutes=5),
        **remplacements: str | None,
    ) -> str:
        defaut = REVENDICATIONS_CITOYEN if role == "citoyen" else REVENDICATIONS_AGENT
        revendications: dict[str, Any] = {
            "role": role,
            "exp": datetime.now(timezone.utc) + expire_dans,
            **defaut,
            **remplacements,
        }
        revendications = {nom: valeur for nom, valeur in revendications.items() if valeur is not None}
        return jwt.encode(revendications, cle, algorithm="EdDSA")

    return signer


# Le jeton arrive au service par le cookie de session de l'application, ou par l'en-tête Authorization.
def _par_cookie(jeton: str) -> dict[str, str]:
    return {"Cookie": f"__Host-session={jeton}"}


def _par_porteur(jeton: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {jeton}"}


@pytest.fixture(params=[_par_cookie, _par_porteur], ids=["cookie", "porteur"])
def transport(request: pytest.FixtureRequest) -> Callable[[str], dict[str, str]]:
    """Les en-têtes qui portent un jeton : `transport(jeton)`. Un test qui le demande passe par les deux voies."""
    porter: Callable[[str], dict[str, str]] = request.param
    return porter


# Balises dont le contenu n'apparaît pas dans la page affichée.
BALISES_INVISIBLES = {"title", "script", "style", "template"}


class _LecteurDeTexteVisible(HTMLParser):
    """Recueille le texte qu'un lecteur voit dans la page : ni balises, ni commentaires, ni scripts."""

    def __init__(self) -> None:
        super().__init__()
        self.morceaux: list[str] = []
        self._dans_une_balise_invisible = 0

    def handle_starttag(self, tag: str, attrs: object) -> None:
        if tag in BALISES_INVISIBLES:
            self._dans_une_balise_invisible += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in BALISES_INVISIBLES and self._dans_une_balise_invisible:
            self._dans_une_balise_invisible -= 1

    def handle_data(self, data: str) -> None:
        if not self._dans_une_balise_invisible:
            self.morceaux.append(data)


def _texte_visible(html: str) -> str:
    lecteur = _LecteurDeTexteVisible()
    lecteur.feed(html)
    return " ".join(" ".join(lecteur.morceaux).split())


def _accueil(client: httpx.Client, jeton: str | None) -> str:
    """Le HTML de l'accueil d'une application. `jeton` voyage dans le cookie de session, comme depuis un navigateur."""
    reponse = client.get("/", headers=_par_cookie(jeton) if jeton else None)
    assert reponse.status_code == 200
    assert reponse.headers["content-type"].startswith("text/html")
    return reponse.text


@pytest.fixture(scope="session")
def page(application: Callable[[str], httpx.Client]) -> Callable[..., str]:
    """Le texte qu'un lecteur voit sur l'accueil d'une application : `page("soin", jeton=…)`."""

    def lire(acteur: str, *, jeton: str | None = None) -> str:
        return _texte_visible(_accueil(application(acteur), jeton))

    return lire


@pytest.fixture(scope="session")
def html_de_page(application: Callable[[str], httpx.Client]) -> Callable[..., str]:
    """Tout le HTML de l'accueil d'une application, balises et scripts compris : `html_de_page("citoyen", jeton=…)`."""

    def lire(acteur: str, *, jeton: str | None = None) -> str:
        return _accueil(application(acteur), jeton)

    return lire


def _sans_signature(signer: Callable[..., str]) -> str:
    """Un jeton de médecin dont l'en-tête annonce l'algorithme `none`, et sans signature."""
    _, charge, _ = signer("médecin").split(".")
    entete = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').rstrip(b"=").decode()
    return f"{entete}.{charge}."


def _charge_modifiee(signer: Callable[..., str]) -> str:
    """La signature d'un jeton de caissier sous les revendications d'un jeton de médecin."""
    entete, _, signature = signer("caissier").split(".")
    _, charge, _ = signer("médecin").split(".")
    return f"{entete}.{charge}.{signature}"


JETONS_INVALIDES = [
    pytest.param(lambda signer: "pas-un-jeton", id="malformé"),
    pytest.param(lambda signer: signer("médecin", expire_dans=timedelta(minutes=-1)), id="expiré"),
    pytest.param(lambda signer: signer("médecin", expire_dans=timedelta(days=365)), id="valable un an"),
    pytest.param(
        lambda signer: signer("médecin", cle=Ed25519PrivateKey.generate()), id="signé d'une autre clé"
    ),
    pytest.param(_sans_signature, id="non signé"),
    pytest.param(_charge_modifiee, id="revendications modifiées"),
    pytest.param(lambda signer: signer("médecin", etablissement=None), id="médecin sans établissement"),
    pytest.param(lambda signer: signer("médecin", npi="0000000001"), id="médecin portant un NPI"),
    pytest.param(lambda signer: signer("citoyen", npi=None), id="citoyen sans NPI"),
    pytest.param(
        lambda signer: signer("citoyen", etablissement="etablissement-test-1"),
        id="citoyen rattaché à un établissement",
    ),
    pytest.param(lambda signer: signer("administrateur"), id="rôle inconnu"),
]


@pytest.fixture(params=JETONS_INVALIDES)
def jeton_invalide(request: pytest.FixtureRequest, signer_jeton: Callable[..., str]) -> str:
    """Un jeton que tout service refuse par 401, quel que soit le rôle qu'il sert. Un test par cas."""
    forger: Callable[[Callable[..., str]], str] = request.param
    return forger(signer_jeton)
