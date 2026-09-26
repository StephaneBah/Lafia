"""Chaque acteur : son application sur <acteur>.<domaine>, son service sous <acteur>.<domaine>/api/<acteur>/*.

Chaque ligne de `ACTEURS` soumet un acteur aux mêmes vérifications que les autres, sauf la session
admise : celle d'un agent porte son établissement, celle de l'officine n'en porte aucun, celle du
citoyen se vérifie dans `tests/test_citoyen.py`. Les jetons valides viennent
de connexions avec les comptes de démonstration. Un nouvel acteur s'ajoute aussi à
`tests/test_identite.py` et aux sondes de `tests/test_isolement.py`.
"""

from typing import NamedTuple

import pytest

from conftest import COOKIE_DE_RENOUVELLEMENT, COOKIE_DE_SESSION, cookies_poses, par_cookie


class Acteur(NamedTuple):
    titre: str
    """Ce que son application affiche en titre."""
    roles_admis: tuple[str, ...]
    """Les rôles que son service sert ; il refuse tous les autres."""


ACTEURS = {
    "soin": Acteur("Soin", ("médecin", "infirmier")),
    "caisse": Acteur("Caisse", ("caissier",)),
    "pharmacie": Acteur("Pharmacie", ("pharmacien", "officine")),
    "citoyen": Acteur("Mon carnet", ("citoyen",)),
}
ROLES = ("médecin", "infirmier", "caissier", "pharmacien", "officine", "citoyen")

# Les agents que chaque service sert : leur session porte un établissement.
AGENTS_ADMIS = [
    (nom, role)
    for nom, acteur in ACTEURS.items()
    for role in acteur.roles_admis
    if role not in ("officine", "citoyen")
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


# Les applications où un agent ou une officine se connecte ; celle du citoyen attend F6.
APPLICATIONS_D_AGENTS = ["soin", "caisse", "pharmacie"]


@pytest.fixture(scope="session")
def noms(jeu) -> dict[str, str]:
    """Le nom affiché de chaque agent, établissement et officine du jeu, par identifiant."""
    return {
        **{a["id"]: a["nom"] for a in jeu("agents")["agent"]},
        **{s["id"]: s["nom"] for s in [*jeu("etablissements")["etablissement"], *jeu("officines")["officine"]]},
    }


@pytest.mark.parametrize(("acteur", "role"), AGENTS_ADMIS)
def test_application_nomme_l_agent_connecte_et_son_etablissement(page, compte_de, jeton_de, noms, acteur, role):
    compte = compte_de(role)

    texte = page(acteur, jeton=jeton_de(role))

    assert f"Connecté comme {role}" in texte
    assert noms[compte.sub] in texte
    assert f"Établissement {noms[compte.etablissement]}" in texte
    assert "Se déconnecter" in texte


def test_application_pharmacie_nomme_l_officine_connectee(page, compte_de, jeton_de, noms):
    texte = page("pharmacie", jeton=jeton_de("officine"))

    assert "Connecté comme officine" in texte
    assert noms[compte_de("officine").sub] in texte
    assert "Se déconnecter" in texte


@pytest.mark.parametrize("acteur", APPLICATIONS_D_AGENTS)
def test_accueil_sans_session_mene_a_la_page_de_connexion(page, html_de_page, acteur):
    assert "Se connecter" in page(acteur)
    assert 'href="/connexion"' in html_de_page(acteur)


@pytest.mark.parametrize("acteur", APPLICATIONS_D_AGENTS)
def test_page_de_connexion_liste_les_comptes_de_demonstration_de_l_application(
    page, html_de_page, comptes, acteur
):
    texte = page(acteur, "/connexion")
    html = html_de_page(acteur, "/connexion")

    assert 'action="/api/identite/connexion"' in html
    listes = [c for c in comptes if c.application == acteur and not c.reserve_aux_tests]
    assert [c.identifiant for c in listes if f"{c.identifiant} {c.mot_de_passe}" not in texte] == []
    non_listes = [c for c in comptes if c.application != acteur or c.reserve_aux_tests]
    assert [c.identifiant for c in non_listes if c.identifiant in html] == []


MESSAGES_DE_REFUS = {
    "identifiants": "Identifiant ou mot de passe incorrect.",
    "application": "Ce compte n'ouvre pas cette application.",
    "verrouille": "Trop d'essais : réessayez dans 15 minutes.",
}


@pytest.mark.parametrize("erreur", MESSAGES_DE_REFUS)
def test_page_de_connexion_explique_chaque_refus(page, erreur):
    assert MESSAGES_DE_REFUS[erreur] in page("soin", f"/connexion?erreur={erreur}")


@pytest.mark.parametrize("acteur", APPLICATIONS_D_AGENTS)
def test_application_renouvelle_un_jeton_expire_avant_de_rendre_la_page(application, comptes, connecter, acteur):
    compte = next(c for c in comptes if c.application == acteur and not c.reserve_aux_tests)
    identifiant_de_session = cookies_poses(connecter(compte))[COOKIE_DE_RENOUVELLEMENT].value

    # Le navigateur a laissé tomber le cookie du jeton à son expiration ; il garde celui de la session.
    reponse = application(acteur).get(
        "/?onglet=1", headers=par_cookie(**{COOKIE_DE_RENOUVELLEMENT: identifiant_de_session})
    )

    assert (reponse.status_code, reponse.headers.get("location")) == (303, "/?onglet=1")
    assert set(cookies_poses(reponse)) == {COOKIE_DE_SESSION, COOKIE_DE_RENOUVELLEMENT}
    assert cookies_poses(reponse)[COOKIE_DE_SESSION].value


@pytest.mark.parametrize("acteur", APPLICATIONS_D_AGENTS)
def test_application_rend_la_page_sans_session_quand_la_session_est_finie(application, acteur):
    reponse = application(acteur).get("/", headers=par_cookie(**{COOKIE_DE_RENOUVELLEMENT: "session-finie"}))

    assert reponse.status_code == 200
    assert {nom: cookie["max-age"] for nom, cookie in cookies_poses(reponse).items()} == {
        COOKIE_DE_SESSION: "0",
        COOKIE_DE_RENOUVELLEMENT: "0",
    }


@pytest.mark.parametrize("acteur", ACTEURS)
def test_session_sans_jeton_refusee(application, acteur):
    reponse = application(acteur).get(f"/api/{acteur}/session")

    assert reponse.status_code == 401


@pytest.mark.parametrize(("acteur", "role"), AGENTS_ADMIS)
def test_session_rend_l_agent_connecte_par_son_practitioner(
    application, compte_de, jeton_de, transport, acteur, role
):
    compte = compte_de(role)

    reponse = application(acteur).get(f"/api/{acteur}/session", headers=transport(jeton_de(role)))

    assert reponse.status_code == 200
    assert reponse.json() == {"sub": compte.sub, "role": role, "etablissement": compte.etablissement}


def test_session_de_pharmacie_rend_l_officine_connectee_par_son_organization(
    application, compte_de, jeton_de, transport
):
    reponse = application("pharmacie").get("/api/pharmacie/session", headers=transport(jeton_de("officine")))

    assert reponse.status_code == 200
    assert reponse.json() == {"sub": compte_de("officine").sub, "role": "officine"}


@pytest.mark.parametrize("acteur", ACTEURS)
def test_session_refuse_un_jeton_invalide(application, transport, jeton_invalide, acteur):
    reponse = application(acteur).get(f"/api/{acteur}/session", headers=transport(jeton_invalide))

    assert reponse.status_code == 401


@pytest.mark.parametrize(("acteur", "role"), ROLES_REFUSES)
def test_session_refuse_un_role_que_le_service_ne_sert_pas(application, jeton_de, transport, acteur, role):
    reponse = application(acteur).get(f"/api/{acteur}/session", headers=transport(jeton_de(role)))

    assert reponse.status_code == 403


@pytest.mark.parametrize(("acteur", "autre"), AUTRES_ACTEURS)
def test_sous_domaine_sans_route_vers_le_service_d_un_autre_acteur(application, acteur, autre):
    # /sante répond 200 à qui la joint : un 404 dit que la passerelle n'y mène pas.
    reponse = application(acteur).get(f"/api/{autre}/sante")

    assert reponse.status_code == 404


# Chemins qu'aucun sous-domaine ne sert : ni le noyau, ni une API inconnue, ni la racine des API.
CHEMINS_FERMES = ["/fhir/metadata", "/api/fhir/metadata", "/api/", "/api/inconnu/sante"]


@pytest.mark.parametrize("chemin", CHEMINS_FERMES)
@pytest.mark.parametrize("acteur", ACTEURS)
def test_sous_domaine_sans_route_hors_de_son_service_et_d_identite(application, acteur, chemin):
    reponse = application(acteur).get(chemin)

    assert reponse.status_code == 404


# Posés par la passerelle sur toute réponse : pages de l'application, API de son service, refus.
EN_TETES_DE_SECURITE = {
    "strict-transport-security": "max-age=31536000",
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "content-security-policy": "frame-ancestors 'none'",
    "referrer-policy": "same-origin",
    "permissions-policy": "geolocation=(), microphone=()",
}
# Ce qui nommerait le logiciel derrière la passerelle.
EN_TETES_BAVARDS = ["server", "x-powered-by", "via"]


@pytest.mark.parametrize("chemin", ["/", "/api/{acteur}/sante", "/api/inconnu/sante"])
@pytest.mark.parametrize("acteur", ACTEURS)
def test_reponse_porte_les_en_tetes_de_securite_sans_nommer_le_logiciel(application, acteur, chemin):
    reponse = application(acteur).get(chemin.format(acteur=acteur))

    assert {nom: reponse.headers.get(nom) for nom in EN_TETES_DE_SECURITE} == EN_TETES_DE_SECURITE
    assert [nom for nom in EN_TETES_BAVARDS if nom in reponse.headers] == []
