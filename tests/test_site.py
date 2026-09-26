"""Le site produit, sur le domaine lui-même : la vision, et une porte vers chaque application.

Il n'appelle aucun service et n'en expose aucun. Les comptes de démonstration qu'il montre doivent
ouvrir leur application : chacun est l'un de ceux qu'identite liste pour elle.
"""

import re
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


def _comptes_montres(html: str) -> dict[str, list[tuple[str, str]]]:
    """Par application, les comptes que montre sa carte de service : deux valeurs chacun."""
    montres: dict[str, list[tuple[str, str]]] = {}
    for carte in html.split('class="lf-service"')[1:]:
        porte = re.search(rf'href="https://(\w+)\.{re.escape(DOMAINE)}"', carte)
        assert porte, "une carte de service sans lien vers son application"
        valeurs = re.findall(r'<code class="lf-demo-v"[^>]*>([^<]*)</code>', carte)
        assert valeurs and len(valeurs) % 2 == 0, f"carte {porte[1]} : des comptes incomplets"
        montres[porte[1]] = list(zip(valeurs[::2], valeurs[1::2]))
    return montres


def test_site_montre_des_comptes_pour_chaque_application(html_du_site):
    assert sorted(_comptes_montres(html_du_site)) == sorted(ACTEURS)


@pytest.mark.parametrize("acteur", ACTEURS)
def test_comptes_du_site_connus_d_identite(html_du_site, application, acteur):
    listes = application(acteur).get("/api/identite/comptes-de-demonstration")
    assert listes.status_code == 200
    connus = {
        (compte["npi"], compte["code"]) if compte["role"] == "citoyen" else (compte["identifiant"], compte["mot_de_passe"])
        for compte in listes.json()
    }

    assert set(_comptes_montres(html_du_site)[acteur]) <= connus
