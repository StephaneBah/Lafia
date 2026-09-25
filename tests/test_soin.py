"""Acteur soin : son application sur soin.<domaine>, son service sous soin.<domaine>/api/soin/*."""

import base64
from datetime import timedelta
from html.parser import HTMLParser

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


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


def texte_visible(html: str) -> str:
    lecteur = _LecteurDeTexteVisible()
    lecteur.feed(html)
    return " ".join(" ".join(lecteur.morceaux).split())


# Le jeton arrive par le cookie de session de l'application, ou par l'en-tête Authorization.
def par_cookie(jeton: str) -> dict[str, str]:
    return {"Cookie": f"__Host-session={jeton}"}


def par_porteur(jeton: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {jeton}"}


def test_sante_soin_rapporte_la_version_fhir_du_noyau(application):
    reponse = application("soin").get("/api/soin/sante")

    assert reponse.status_code == 200
    assert reponse.json() == {
        "service": "soin",
        "statut": "disponible",
        "noyau": {"statut": "disponible", "version_fhir": "4.0.1"},
    }


def test_documentation_openapi_de_soin_joignable_par_la_passerelle(application):
    soin = application("soin")

    contrat = soin.get("/api/soin/openapi.json")
    assert contrat.status_code == 200
    assert "/api/soin/sante" in contrat.json()["paths"]

    documentation = soin.get("/api/soin/docs")
    assert documentation.status_code == 200
    assert "/api/soin/openapi.json" in documentation.text


def test_application_soin_affiche_son_service_et_la_version_fhir_du_noyau(application):
    page = application("soin").get("/")

    assert page.status_code == 200
    assert page.headers["content-type"].startswith("text/html")
    texte = texte_visible(page.text)
    assert "Soin" in texte
    assert "Service soin disponible" in texte
    assert "Noyau disponible, FHIR 4.0.1" in texte
    assert "Session aucune" in texte


def test_application_soin_affiche_le_soignant_connecte(application, signer_jeton):
    cookie = par_cookie(signer_jeton("infirmier", etablissement="etablissement-test-3"))

    page = application("soin").get("/", headers=cookie)

    assert page.status_code == 200
    texte = texte_visible(page.text)
    assert "Connecté comme infirmier" in texte
    assert "Établissement etablissement-test-3" in texte


def test_session_soin_sans_jeton_refusee(application):
    reponse = application("soin").get("/api/soin/session")

    assert reponse.status_code == 401


@pytest.mark.parametrize("transport", [par_cookie, par_porteur])
@pytest.mark.parametrize("role", ["médecin", "infirmier"])
def test_session_soin_rend_le_soignant_du_jeton(application, signer_jeton, role, transport):
    jeton = signer_jeton(role, sub="agent-test-7", etablissement="etablissement-test-3")

    reponse = application("soin").get("/api/soin/session", headers=transport(jeton))

    assert reponse.status_code == 200
    assert reponse.json() == {
        "sub": "agent-test-7",
        "role": role,
        "etablissement": "etablissement-test-3",
    }


def _sans_signature(signer_jeton) -> str:
    """Un jeton de médecin dont l'en-tête annonce l'algorithme `none`, et sans signature."""
    _, charge, _ = signer_jeton("médecin").split(".")
    entete = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').rstrip(b"=").decode()
    return f"{entete}.{charge}."


def _charge_modifiee(signer_jeton) -> str:
    """La signature d'un jeton de caissier sous les revendications d'un jeton de médecin."""
    entete, _, signature = signer_jeton("caissier").split(".")
    _, charge, _ = signer_jeton("médecin").split(".")
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
    pytest.param(lambda signer: signer("administrateur"), id="rôle inconnu"),
]


@pytest.mark.parametrize("forger", JETONS_INVALIDES)
def test_session_soin_refuse_un_jeton_invalide(application, signer_jeton, forger):
    reponse = application("soin").get("/api/soin/session", headers=par_cookie(forger(signer_jeton)))

    assert reponse.status_code == 401


@pytest.mark.parametrize("role", ["caissier", "pharmacien", "citoyen"])
def test_session_soin_refuse_un_role_hors_du_soin(application, signer_jeton, role):
    reponse = application("soin").get("/api/soin/session", headers=par_cookie(signer_jeton(role)))

    assert reponse.status_code == 403
