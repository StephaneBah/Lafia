"""Le site produit, sur le domaine lui-même : la vision, et une porte vers chaque application.

Il n'appelle aucun service et n'en expose aucun. Il ne montre aucun compte de démonstration : ceux-ci
sont sur la page de connexion de chaque application.
"""

from collections.abc import Iterator

import httpx
import pytest

from conftest import ADRESSE, DOMAINE, _contexte_tls, _texte_visible, _VersAdresse
from test_acteurs import ACTEURS, EN_TETES_BAVARDS, EN_TETES_DE_SECURITE


@pytest.fixture(scope="module")
def site() -> Iterator[httpx.Client]:
    """Client du site, adressé par le domaine lui-même sur la passerelle."""
    contexte = _contexte_tls()
    transport = _VersAdresse(ADRESSE, verify=contexte) if ADRESSE else httpx.HTTPTransport(verify=contexte)
    with httpx.Client(base_url=f"https://{DOMAINE}", transport=transport, timeout=10) as client:
        yield client


@pytest.fixture(scope="module")
def html_du_site(site: httpx.Client) -> str:
    reponse = site.get("/")
    assert reponse.status_code == 200
    assert reponse.headers["content-type"].startswith("text/html")
    return reponse.text


def test_site_servi_sur_le_domaine(html_du_site):
    assert "Votre dossier de santé vous suit, partout au Bénin." in _texte_visible(html_du_site)


@pytest.mark.parametrize("acteur", ACTEURS)
def test_site_mene_a_chaque_application(html_du_site, acteur):
    assert f'href="https://{acteur}.{DOMAINE}"' in html_du_site


@pytest.mark.parametrize("chemin", ["/", "/api/identite/sante"])
def test_site_porte_les_en_tetes_de_securite_sans_nommer_le_logiciel(site, chemin):
    reponse = site.get(chemin)

    assert {nom: reponse.headers.get(nom) for nom in EN_TETES_DE_SECURITE} == EN_TETES_DE_SECURITE
    assert [nom for nom in EN_TETES_BAVARDS if nom in reponse.headers] == []


@pytest.mark.parametrize("chemin", ["/api/identite/comptes-de-demonstration", "/api/soin/sante", "/api/inconnu"])
def test_site_n_ouvre_aucun_service(site, chemin):
    assert site.get(chemin).status_code == 404


def test_site_ne_montre_aucun_compte(html_du_site):
    """Le site présente le produit ; les comptes de démonstration restent sur /connexion."""
    assert "lf-demo" not in html_du_site
    assert "lafia-demo" not in html_du_site
    assert "compte de démonstration" not in _texte_visible(html_du_site).lower()
