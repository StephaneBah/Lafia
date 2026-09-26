"""Chaque acteur : son application sur <acteur>.<domaine>, son service sous <acteur>.<domaine>/api/<acteur>/*.

Chaque ligne de `ACTEURS` soumet un acteur aux mêmes vérifications que les autres, sauf la session
admise : celle d'un agent porte son établissement, celle du citoyen se vérifie dans
`tests/test_citoyen.py`. Un nouvel acteur s'ajoute aussi à `tests/test_identite.py` et aux sondes de
`tests/test_isolement.py`.
"""

from typing import NamedTuple

import pytest


class Acteur(NamedTuple):
    titre: str
    """Ce que son application affiche en titre."""
    roles_admis: tuple[str, ...]
    """Les rôles que son service sert ; il refuse tous les autres."""


ACTEURS = {
    "soin": Acteur("Soin", ("médecin", "infirmier")),
    "caisse": Acteur("Caisse", ("caissier",)),
    "pharmacie": Acteur("Pharmacie", ("pharmacien",)),
    "citoyen": Acteur("Mon carnet", ("citoyen",)),
}
ROLES = ("médecin", "infirmier", "caissier", "pharmacien", "citoyen")

# Les agents que chaque service sert : leur session porte un établissement.
AGENTS_ADMIS = [
    (nom, role) for nom, acteur in ACTEURS.items() for role in acteur.roles_admis if role != "citoyen"
]
ROLES_REFUSES = [
    (nom, role) for nom, acteur in ACTEURS.items() for role in ROLES if role not in acteur.roles_admis
]
AUTRES_ACTEURS = [(nom, autre) for nom in ACTEURS for autre in ACTEURS if autre != nom]


@pytest.mark.parametrize("acteur", ACTEURS)
def test_sante_rapporte_la_version_fhir_du_noyau(application, acteur):
    reponse = application(acteur).get(f"/api/{acteur}/sante")

    assert reponse.status_code == 200
    assert reponse.json() == {
        "service": acteur,
        "statut": "disponible",
        "noyau": {"statut": "disponible", "version_fhir": "4.0.1"},
    }


@pytest.mark.parametrize("acteur", ACTEURS)
def test_documentation_openapi_joignable_par_la_passerelle(application, acteur):
    client = application(acteur)

    contrat = client.get(f"/api/{acteur}/openapi.json")
    assert contrat.status_code == 200
    assert {f"/api/{acteur}/sante", f"/api/{acteur}/session"} <= set(contrat.json()["paths"])

    documentation = client.get(f"/api/{acteur}/docs")
    assert documentation.status_code == 200
    assert f"/api/{acteur}/openapi.json" in documentation.text


@pytest.mark.parametrize("acteur", ACTEURS)
def test_application_affiche_son_service_et_la_version_fhir_du_noyau(page, acteur):
    texte = page(acteur)

    assert ACTEURS[acteur].titre in texte
    assert f"Service {acteur} disponible" in texte
    assert "Noyau disponible, FHIR 4.0.1" in texte
    assert "Session aucune" in texte


@pytest.mark.parametrize(("acteur", "role"), AGENTS_ADMIS)
def test_application_affiche_l_agent_connecte(page, signer_jeton, acteur, role):
    texte = page(acteur, jeton=signer_jeton(role, etablissement="etablissement-test-3"))

    assert f"Connecté comme {role}" in texte
    assert "Établissement etablissement-test-3" in texte


@pytest.mark.parametrize("acteur", ACTEURS)
def test_session_sans_jeton_refusee(application, acteur):
    reponse = application(acteur).get(f"/api/{acteur}/session")

    assert reponse.status_code == 401


@pytest.mark.parametrize(("acteur", "role"), AGENTS_ADMIS)
def test_session_rend_l_agent_du_jeton(application, signer_jeton, transport, acteur, role):
    jeton = signer_jeton(role, sub="agent-test-7", etablissement="etablissement-test-3")

    reponse = application(acteur).get(f"/api/{acteur}/session", headers=transport(jeton))

    assert reponse.status_code == 200
    assert reponse.json() == {
        "sub": "agent-test-7",
        "role": role,
        "etablissement": "etablissement-test-3",
    }


@pytest.mark.parametrize("acteur", ACTEURS)
def test_session_refuse_un_jeton_invalide(application, transport, jeton_invalide, acteur):
    reponse = application(acteur).get(f"/api/{acteur}/session", headers=transport(jeton_invalide))

    assert reponse.status_code == 401


@pytest.mark.parametrize(("acteur", "role"), ROLES_REFUSES)
def test_session_refuse_un_role_que_le_service_ne_sert_pas(
    application, signer_jeton, transport, acteur, role
):
    reponse = application(acteur).get(f"/api/{acteur}/session", headers=transport(signer_jeton(role)))

    assert reponse.status_code == 403


@pytest.mark.parametrize(("acteur", "autre"), AUTRES_ACTEURS)
def test_sous_domaine_sans_route_vers_le_service_d_un_autre_acteur(application, acteur, autre):
    # /sante répond 200 à qui la joint : un 404 dit que la passerelle n'y mène pas.
    reponse = application(acteur).get(f"/api/{autre}/sante")

    assert reponse.status_code == 404
