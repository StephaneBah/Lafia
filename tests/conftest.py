"""Suite boîte noire : elle observe la pile en marche du dehors, comme un usager ou un attaquant.

Chaque application est jointe par son sous-domaine, `<application>.<domaine>`.
La même suite vise la pile locale ou l'adresse publique selon l'environnement :

- `LAFIA_DOMAINE` : domaine de base, `localhost` par défaut.
- `LAFIA_ADRESSE` : adresse IP où joindre la passerelle. Par défaut `127.0.0.1` pour
  `localhost` (tous les systèmes ne résolvent pas `*.localhost`), le DNS sinon.

Les certificats sont vérifiés : en local contre l'autorité interne de Caddy, lue dans le
conteneur de la passerelle ; ailleurs contre les autorités publiques.

Tout passe par la passerelle, sauf l'isolement réseau et le contenu du noyau, qui ne s'y observent
pas : ces vérifications passent par `docker`, sur la machine de la pile visée, et sont sautées quand
elle tourne ailleurs.

Les jetons valides viennent de connexions par identite, avec les comptes de démonstration lus dans
`donnees/` : la suite ne tient jamais la clé privée d'une pile déployée. Les jetons mal formés ne se
forgent qu'avec la clé de développement, que seule une pile servie sur localhost accepte : ces tests
sont sautés ailleurs.
"""

import base64
import json
import os
import ssl
import subprocess
import tomllib
from collections.abc import Callable, Iterator
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from http.cookiejar import CookieJar, DefaultCookiePolicy
from http.cookies import Morsel, SimpleCookie
from pathlib import Path
from types import EllipsisType
from typing import Any, NamedTuple

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import load_der_private_key

RACINE_DU_DEPOT = Path(__file__).resolve().parent.parent
RACINE_CA_CADDY = "/data/caddy/pki/authorities/local/root.crt"
# Les fichiers du jeu de démonstration, que la pile charge dans le noyau à chaque démarrage.
JEU_DE_DEMONSTRATION = RACINE_DU_DEPOT / "donnees" / "src" / "donnees"

DOMAINE = os.environ.get("LAFIA_DOMAINE", "localhost")
LOCAL = DOMAINE == "localhost"
ADRESSE = os.environ.get("LAFIA_ADRESSE") or ("127.0.0.1" if LOCAL else None)

# Clé privée de la paire de développement. Elle n'a rien de secret : une pile servie sur localhost,
# sans JETON_CLE_PUBLIQUE, accepte les jetons qu'elle signe ; toute autre pile refuse sa clé publique
# (commun/src/commun/jeton.py).
CLE_PRIVEE_DE_DEVELOPPEMENT = "MC4CAQAwBQYDK2VwBCIEINp8yVHhQe5B/gcbA5wNMNwe0d+oaAY7090L95AC8EvZ"

# Revendications d'un jeton forgé, par rôle : identifiants synthétiques seulement.
REVENDICATIONS_AGENT = {"sub": "agent-test-1", "etablissement": "etablissement-test-1"}
REVENDICATIONS_OFFICINE: dict[str, str] = {"sub": "officine-test-1"}
REVENDICATIONS_CITOYEN = {"sub": "citoyen-test-1", "npi": "0000000001"}

# Les cookies que identite pose à la connexion, sur le sous-domaine de l'application (ADR 0004).
COOKIE_DE_SESSION = "__Host-session"
COOKIE_DE_RENOUVELLEMENT = "__Host-renouvellement"

# Un rôle, une application : où chaque rôle se connecte (ADR 0004).
APPLICATION_DU_ROLE = {
    "médecin": "soin",
    "infirmier": "soin",
    "caissier": "caisse",
    "pharmacien": "pharmacie",
    "officine": "pharmacie",
    "citoyen": "citoyen",
}


class _VersAdresse(httpx.HTTPTransport):
    """Joint la passerelle à une adresse fixe, en gardant le sous-domaine pour Host et SNI."""

    def __init__(self, adresse: str, **options: Any) -> None:
        super().__init__(**options)
        self._adresse = adresse

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        request.extensions["sni_hostname"] = request.url.host
        request.url = request.url.copy_with(host=self._adresse)
        return super().handle_request(request)


def _docker(*arguments: str, entree: str | None = None) -> subprocess.CompletedProcess[str]:
    """La commande `docker`, lancée depuis la racine du dépôt, où `docker compose` trouve la pile.

    `entree` est écrite sur son entrée standard.
    """
    return subprocess.run(
        ["docker", *arguments],
        cwd=RACINE_DU_DEPOT,
        input=entree,
        capture_output=True,
        text=True,
        encoding="utf-8",
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


class Reponse(NamedTuple):
    """Ce que le noyau répond à une lecture : son statut HTTP, et la ressource quand il en rend une."""

    statut: int
    ressource: dict[str, Any] | None


# Lit le noyau depuis un service qui parle FHIR : chemins FHIR en JSON sur l'entrée standard, une
# réponse par chemin sur la sortie. Une recherche est lue en entier, ses pages suivantes ajoutées à la
# première. Rien d'autre que des GET : la lecture ne change pas ce qu'elle observe.
LECTEUR_DU_NOYAU = """
import json, os, sys, urllib.error, urllib.request

def lire(adresse):
    requete = urllib.request.Request(adresse, headers={"Accept": "application/fhir+json"})
    try:
        with urllib.request.urlopen(requete, timeout=30) as reponse:
            return reponse.status, json.load(reponse)
    except urllib.error.HTTPError as erreur:
        return erreur.code, None

def suivante(page):
    return next((lien["url"] for lien in page.get("link", []) if lien["relation"] == "next"), None)

reponses = []
for chemin in json.load(sys.stdin):
    statut, ressource = lire(f"{os.environ['NOYAU_URL']}/{chemin}")
    page = ressource
    while page and page.get("resourceType") == "Bundle" and suivante(page):
        _, page = lire(suivante(page))
        ressource.setdefault("entry", []).extend(page.get("entry", []))
    reponses.append([statut, ressource])
json.dump(reponses, sys.stdout)
"""


@pytest.fixture(scope="session")
def noyau(docker: Callable[..., subprocess.CompletedProcess[str]]) -> Callable[[list[str]], list[Reponse]]:
    """Lit le noyau de l'intérieur de la pile : `noyau(["Organization/cnhu-hkm", "Patient?identifier=…"])`.

    Le noyau ne s'observe pas par la passerelle : la lecture part du conteneur soin, qui le joint.
    Une réponse par chemin, dans l'ordre des chemins. Sautée comme `docker` quand la pile tourne ailleurs.
    """

    def lire(chemins: list[str]) -> list[Reponse]:
        lecture = docker(
            "compose", "exec", "-T", "soin", "python", "-c", LECTEUR_DU_NOYAU, entree=json.dumps(chemins)
        )
        assert lecture.returncode == 0, lecture.stderr
        return [Reponse(statut, ressource) for statut, ressource in json.loads(lecture.stdout)]

    return lire


@pytest.fixture(scope="session")
def jeu() -> Callable[[str], dict[str, Any]]:
    """Un fichier du jeu de démonstration, tel qu'il est écrit : `jeu("patients")["patient"]`."""

    def lire(fichier: str) -> dict[str, Any]:
        return tomllib.loads((JEU_DE_DEMONSTRATION / f"{fichier}.toml").read_text(encoding="utf-8"))

    return lire


@pytest.fixture(scope="session")
def application() -> Iterator[Callable[[str], httpx.Client]]:
    """Client HTTP d'une application, adressée par son sous-domaine sur la passerelle.

    Un client par application : chaque sous-domaine garde ses propres connexions TLS. Il ne garde
    aucun cookie : chaque test porte les siens, et une connexion ne se glisse pas dans un autre test.
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
                base_url=origine_de(nom),
                transport=transport,
                timeout=10,
                cookies=CookieJar(policy=DefaultCookiePolicy(allowed_domains=[])),
            )
        return clients[nom]

    yield client_de
    for client in clients.values():
        client.close()


def origine_de(application: str) -> str:
    """L'origine des pages d'une application, celle que le navigateur envoie avec ses formulaires."""
    return f"https://{application}.{DOMAINE}"


class Compte(NamedTuple):
    """Un compte d'agent ou d'officine, tel que le jeu de démonstration l'écrit."""

    identifiant: str
    mot_de_passe: str
    role: str
    sub: str
    """Le Practitioner de l'agent, ou l'Organization de l'officine."""
    etablissement: str | None
    """L'Organization de l'établissement de l'agent ; aucune pour une officine."""
    reserve_aux_tests: bool

    @property
    def application(self) -> str:
        return APPLICATION_DU_ROLE[self.role]


class CitoyenDeDemonstration(NamedTuple):
    npi: str
    code: str
    reserve_aux_tests: bool


@pytest.fixture(scope="session")
def comptes(jeu: Callable[[str], dict[str, Any]]) -> list[Compte]:
    """Tous les comptes du jeu de démonstration, réservés aux tests compris."""
    return [
        *(
            Compte(c["identifiant"], c["mot_de_passe"], a["role"], a["id"], c["etablissement"], c.get("reserve_aux_tests", False))
            for a in jeu("agents")["agent"]
            for c in a["compte"]
        ),
        *(
            Compte(o["compte"]["identifiant"], o["compte"]["mot_de_passe"], "officine", o["id"], None, False)
            for o in jeu("officines")["officine"]
        ),
    ]


@pytest.fixture(scope="session")
def compte_de(comptes: list[Compte]) -> Callable[[str], Compte]:
    """Le premier compte de démonstration d'un rôle, jamais un compte réservé aux tests : `compte_de("médecin")`."""

    def premier(role: str) -> Compte:
        return next(c for c in comptes if c.role == role and not c.reserve_aux_tests)

    return premier


@pytest.fixture(scope="session")
def citoyens(jeu: Callable[[str], dict[str, Any]]) -> list[CitoyenDeDemonstration]:
    """Les citoyens de démonstration, réservés aux tests compris."""
    return [
        CitoyenDeDemonstration(c["npi"], c["code_carnet"], c.get("reserve_aux_tests", False))
        for c in jeu("citoyens")["citoyen"]
    ]


@pytest.fixture(scope="session")
def citoyen_de_demonstration(citoyens: list[CitoyenDeDemonstration]) -> CitoyenDeDemonstration:
    """Le citoyen avec lequel la suite se connecte : le dernier réservé aux tests, qu'elle ne verrouille
    jamais, et dont nul autre ne remplace le code."""
    return [c for c in citoyens if c.reserve_aux_tests][-1]


def cookies_poses(reponse: httpx.Response) -> dict[str, Morsel[str]]:
    """Les cookies que pose une réponse, par nom, avec leurs attributs."""
    poses: dict[str, Morsel[str]] = {}
    for entete in reponse.headers.get_list("set-cookie"):
        cookie: SimpleCookie = SimpleCookie()
        cookie.load(entete)
        poses.update(cookie)
    return poses


def par_cookie(**cookies: str) -> dict[str, str]:
    """L'en-tête Cookie qui porte `cookies` : `par_cookie(**{COOKIE_DE_SESSION: jeton})`."""
    return {"Cookie": "; ".join(f"{nom}={valeur}" for nom, valeur in cookies.items())}


def origine_envoyee_par_le_navigateur(politique_de_referent: str, application: str) -> str:
    """L'en-tête Origin qu'un navigateur joint au formulaire POST d'une page HTTPS de `application`
    vers la même origine, selon la politique de référent de la page (Fetch, « append a request Origin
    header ») : `null` sous `no-referrer`, l'origine de la page sous toute autre politique. De
    plusieurs politiques, le navigateur applique la dernière."""
    politique = politique_de_referent.split(",")[-1].strip().lower()
    return "null" if politique == "no-referrer" else origine_de(application)


@pytest.fixture(scope="session")
def formulaire(application: Callable[[str], httpx.Client]) -> Callable[..., httpx.Response]:
    """Envoie un formulaire à identite depuis une page d'une application, comme le navigateur :
    `formulaire("soin", "connexion", identifiant=…, mot_de_passe=…)`.

    L'en-tête Origin est celui qu'un navigateur enverrait depuis la page, selon la politique de
    référent que la passerelle lui pose : un navigateur ne laisse pas une page choisir son origine.
    `origine` le remplace, pour imiter une autre page ; `None` n'en envoie aucun. `cookies` sont ceux
    que le navigateur porte sur ce sous-domaine.
    """
    politiques: dict[str, str] = {}

    def origine_de_la_page(acteur: str) -> str:
        if acteur not in politiques:
            politiques[acteur] = application(acteur).get("/").headers.get("referrer-policy", "")
        return origine_envoyee_par_le_navigateur(politiques[acteur], acteur)

    def envoyer(
        acteur: str,
        chemin: str,
        *,
        origine: str | None | EllipsisType = ...,
        cookies: dict[str, str] | None = None,
        **champs: str,
    ) -> httpx.Response:
        entetes = par_cookie(**cookies) if cookies else {}
        if origine is ...:
            origine = origine_de_la_page(acteur)
        if origine is not None:
            entetes["Origin"] = origine
        return application(acteur).post(f"/api/identite/{chemin}", data=champs, headers=entetes)

    return envoyer


@pytest.fixture(scope="session")
def connecter(formulaire: Callable[..., httpx.Response]) -> Callable[..., httpx.Response]:
    """Connecte un compte depuis la page de connexion de son application, ou de `acteur` :
    `connecter(compte)`. Rend la réponse de identite."""

    def envoyer(compte: Compte, *, acteur: str | None = None, mot_de_passe: str | None = None) -> httpx.Response:
        return formulaire(
            acteur or compte.application,
            "connexion",
            identifiant=compte.identifiant,
            mot_de_passe=compte.mot_de_passe if mot_de_passe is None else mot_de_passe,
        )

    return envoyer


@pytest.fixture(scope="session")
def connecter_citoyen(formulaire: Callable[..., httpx.Response]) -> Callable[..., httpx.Response]:
    """Connecte un citoyen depuis l'application citoyen : `connecter_citoyen(npi, code)`."""

    def envoyer(npi: str, code: str, *, acteur: str = "citoyen") -> httpx.Response:
        return formulaire(acteur, "citoyen/connexion", npi=npi, code=code)

    return envoyer


def jeton_pose(reponse: httpx.Response) -> str:
    """Le jeton que pose une connexion réussie ou un renouvellement."""
    assert reponse.status_code in (204, 303), reponse.text
    return cookies_poses(reponse)[COOKIE_DE_SESSION].value


@pytest.fixture(scope="session")
def jeton_de(
    compte_de: Callable[[str], Compte],
    citoyen_de_demonstration: CitoyenDeDemonstration,
    connecter: Callable[..., httpx.Response],
    connecter_citoyen: Callable[..., httpx.Response],
) -> Callable[[str], str]:
    """Un jeton valide d'un rôle, obtenu en se connectant une fois pour toute la suite : `jeton_de("médecin")`.

    Un agent ou une officine par son premier compte de démonstration ; le citoyen par
    `citoyen_de_demonstration`.
    """
    jetons: dict[str, str] = {}

    def jeton(role: str) -> str:
        if role not in jetons:
            if role == "citoyen":
                reponse = connecter_citoyen(citoyen_de_demonstration.npi, citoyen_de_demonstration.code)
            else:
                reponse = connecter(compte_de(role))
            jetons[role] = jeton_pose(reponse)
        return jetons[role]

    return jeton


@pytest.fixture(scope="session")
def signer_jeton() -> Callable[..., str]:
    """Forge un jeton avec la clé de développement, que seule une pile servie sur localhost accepte :
    `signer_jeton("médecin")`. Ailleurs, le test est sauté : la suite ne tient pas la clé d'une pile déployée.

    Les revendications par défaut du rôle se remplacent par mot-clé ; `None` en retire une.
    `expire_dans` règle l'expiration ; `cle` signe d'une autre clé que celle de la pile visée.
    """
    if not LOCAL:
        pytest.skip(f"jetons forgés avec la clé de développement : la pile qui sert {DOMAINE} les refuse")
    cle_de_la_pile = load_der_private_key(base64.b64decode(CLE_PRIVEE_DE_DEVELOPPEMENT), password=None)
    assert isinstance(cle_de_la_pile, Ed25519PrivateKey)

    def signer(
        role: str,
        *,
        cle: Ed25519PrivateKey = cle_de_la_pile,
        expire_dans: timedelta = timedelta(minutes=5),
        **remplacements: str | None,
    ) -> str:
        defaut = {"citoyen": REVENDICATIONS_CITOYEN, "officine": REVENDICATIONS_OFFICINE}.get(
            role, REVENDICATIONS_AGENT
        )
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
    return par_cookie(**{COOKIE_DE_SESSION: jeton})


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


def _html(client: httpx.Client, chemin: str, jeton: str | None) -> str:
    """Le HTML d'une page d'une application. `jeton` voyage dans le cookie de session, comme depuis un navigateur."""
    reponse = client.get(chemin, headers=_par_cookie(jeton) if jeton else None)
    assert reponse.status_code == 200
    assert reponse.headers["content-type"].startswith("text/html")
    return reponse.text


@pytest.fixture(scope="session")
def page(application: Callable[[str], httpx.Client]) -> Callable[..., str]:
    """Le texte qu'un lecteur voit sur une page d'une application, l'accueil par défaut :
    `page("soin", jeton=…)`, `page("soin", "/connexion")`."""

    def lire(acteur: str, chemin: str = "/", *, jeton: str | None = None) -> str:
        return _texte_visible(_html(application(acteur), chemin, jeton))

    return lire


@pytest.fixture(scope="session")
def html_de_page(application: Callable[[str], httpx.Client]) -> Callable[..., str]:
    """Tout le HTML d'une page d'une application, balises et scripts compris : `html_de_page("citoyen", jeton=…)`."""

    def lire(acteur: str, chemin: str = "/", *, jeton: str | None = None) -> str:
        return _html(application(acteur), chemin, jeton)

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
    pytest.param(
        lambda signer: signer("officine", etablissement="etablissement-test-1"),
        id="officine rattachée à un établissement",
    ),
    pytest.param(lambda signer: signer("officine", npi="0000000001"), id="officine portant un NPI"),
    pytest.param(lambda signer: signer("administrateur"), id="rôle inconnu"),
]


@pytest.fixture(params=JETONS_INVALIDES)
def jeton_invalide(request: pytest.FixtureRequest, signer_jeton: Callable[..., str]) -> str:
    """Un jeton que tout service refuse par 401, quel que soit le rôle qu'il sert. Un test par cas."""
    forger: Callable[[Callable[..., str]], str] = request.param
    return forger(signer_jeton)
