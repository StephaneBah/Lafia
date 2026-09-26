"""Service identite : joint depuis le sous-domaine de chaque application, sous /api/identite/*.

Il connecte les agents et les officines par identifiant et mot de passe, le citoyen par NPI et code
carnet, et pose les deux cookies de la session sur le sous-domaine de l'application (ADR 0004). Les
comptes viennent du jeu de démonstration ; ceux que la suite verrouille exprès lui sont réservés.
"""

import base64
import re
import secrets
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat

from conftest import (
    APPLICATION_DU_ROLE,
    CLE_PRIVEE_DE_DEVELOPPEMENT,
    COOKIE_DE_RENOUVELLEMENT,
    COOKIE_DE_SESSION,
    DOMAINE,
    cookies_poses,
    origine_de,
    origine_envoyee_par_le_navigateur,
    par_cookie,
)

APPLICATIONS = ["soin", "caisse", "pharmacie", "citoyen"]
DUREE_DU_JETON = 15 * 60
INACTIVITE_MAXIMALE_D_UN_AGENT = 30 * 60
DUREE_MAXIMALE_D_UN_CITOYEN = 60 * 60
# Deux groupes de trois caractères, sans 0, O, 1, I ni L.
CODE_CARNET = re.compile(r"[2-9A-HJKMNP-Z]{3}-[2-9A-HJKMNP-Z]{3}")


@pytest.mark.parametrize("acteur", APPLICATIONS)
def test_sante_identite_joignable_depuis_le_sous_domaine_d_une_application(application, acteur):
    reponse = application(acteur).get("/api/identite/sante")

    assert reponse.status_code == 200
    assert reponse.json() == {"service": "identite", "statut": "disponible"}


def _cookies_de_session(reponse):
    """Les deux cookies d'une session ouverte, après vérification des attributs que chacun exige."""
    poses = cookies_poses(reponse)
    assert set(poses) == {COOKIE_DE_SESSION, COOKIE_DE_RENOUVELLEMENT}
    for cookie in poses.values():
        assert cookie["httponly"] is True
        assert cookie["secure"] is True
        assert cookie["samesite"].lower() == "strict"
        assert cookie["path"] == "/"
        assert cookie["domain"] == ""
    return poses


def _duree_de_vie(jeton: str) -> float:
    """Dans combien de secondes le jeton expire. La suite n'en vérifie pas la signature : les services le font."""
    return jwt.decode(jeton, options={"verify_signature": False})["exp"] - time.time()


def test_chaque_compte_de_demonstration_se_connecte_sur_son_application(comptes, connecter):
    # Un compte après l'autre : un échec nomme l'identifiant, public, jamais un mot de passe.
    for compte in [c for c in comptes if not c.reserve_aux_tests]:
        reponse = connecter(compte)

        assert (reponse.status_code, reponse.headers.get("location")) == (303, "/"), compte.identifiant
        poses = _cookies_de_session(reponse)
        assert poses[COOKIE_DE_SESSION]["max-age"] == str(DUREE_DU_JETON)
        assert DUREE_DU_JETON - 60 < _duree_de_vie(poses[COOKIE_DE_SESSION].value) <= DUREE_DU_JETON
        # Un agent ou une officine inactif 30 minutes perd sa session.
        assert poses[COOKIE_DE_RENOUVELLEMENT]["max-age"] == str(INACTIVITE_MAXIMALE_D_UN_AGENT)


def _refus(reponse, erreur: str) -> None:
    """Une connexion refusée : retour à la page de connexion avec la raison, et aucun cookie."""
    assert (reponse.status_code, reponse.headers.get("location")) == (303, f"/connexion?erreur={erreur}")
    assert cookies_poses(reponse) == {}


def test_mauvais_mot_de_passe_et_identifiant_inconnu_recoivent_la_meme_reponse(compte_de, connecter):
    compte = compte_de("médecin")
    inconnu = compte._replace(identifiant=f"inconnu.{secrets.token_hex(4)}")

    mauvais_mot_de_passe = connecter(compte, mot_de_passe="pas-le-bon")
    identifiant_inconnu = connecter(inconnu)
    # Une connexion réussie remet le compteur d'échecs du compte à zéro : la suite ne le rapproche
    # pas d'un verrou, d'un passage à l'autre.
    assert connecter(compte).status_code == 303

    _refus(mauvais_mot_de_passe, "identifiants")
    _refus(identifiant_inconnu, "identifiants")


@pytest.mark.parametrize(
    ("role", "acteur"),
    [
        (role, acteur)
        for role, application_du_role in APPLICATION_DU_ROLE.items()
        if role != "citoyen"
        for acteur in APPLICATIONS
        if acteur != application_du_role
    ],
)
def test_un_compte_ne_se_connecte_pas_sur_l_application_d_un_autre_role(compte_de, connecter, role, acteur):
    reponse = connecter(compte_de(role), acteur=acteur)

    _refus(reponse, "application")


@pytest.mark.parametrize("chemin", ["/", "/connexion"])
@pytest.mark.parametrize("acteur", ["soin", "caisse", "pharmacie"])
def test_depuis_les_pages_d_une_application_le_navigateur_joint_son_origine_aux_formulaires(
    application, acteur, chemin
):
    # Sous la politique `no-referrer`, un navigateur enverrait `Origin: null`, et identite refuserait
    # toute connexion et toute déconnexion.
    politique = application(acteur).get(chemin).headers["referrer-policy"]

    assert origine_envoyee_par_le_navigateur(politique, acteur) == origine_de(acteur)


AUTRES_ORIGINES = [
    pytest.param(None, id="sans origine"),
    pytest.param(origine_de("caisse"), id="une autre application"),
    pytest.param("https://attaquant.example", id="un autre site"),
    pytest.param(f"http://soin.{DOMAINE}", id="la même application en HTTP"),
]


@pytest.mark.parametrize("origine", AUTRES_ORIGINES)
@pytest.mark.parametrize("chemin", ["connexion", "deconnexion"])
def test_un_formulaire_venu_d_une_autre_origine_est_refuse(formulaire, compte_de, chemin, origine):
    compte = compte_de("médecin")

    reponse = formulaire(
        "soin", chemin, origine=origine, identifiant=compte.identifiant, mot_de_passe=compte.mot_de_passe
    )

    assert reponse.status_code == 403
    assert cookies_poses(reponse) == {}


@pytest.mark.parametrize("origine", AUTRES_ORIGINES[1:3])
def test_un_formulaire_citoyen_venu_d_une_autre_origine_est_refuse(formulaire, citoyen_de_demonstration, origine):
    citoyen = citoyen_de_demonstration

    reponse = formulaire("citoyen", "citoyen/connexion", origine=origine, npi=citoyen.npi, code=citoyen.code)

    assert reponse.status_code == 403
    assert cookies_poses(reponse) == {}


def _renouveler(application, acteur: str, identifiant_de_session: str | None):
    """Demande un nouveau jeton, comme le serveur de l'application avant de rendre une page."""
    cookies = par_cookie(**{COOKIE_DE_RENOUVELLEMENT: identifiant_de_session}) if identifiant_de_session else {}
    return application(acteur).post("/api/identite/session/renouveler", headers=cookies)


def _cookies_effaces(reponse) -> None:
    poses = cookies_poses(reponse)
    assert set(poses) == {COOKIE_DE_SESSION, COOKIE_DE_RENOUVELLEMENT}
    assert [(cookie.value, cookie["max-age"]) for cookie in poses.values()] == [("", "0"), ("", "0")]


def test_le_renouvellement_donne_un_jeton_que_les_services_acceptent(application, compte_de, connecter):
    compte = compte_de("caissier")
    identifiant_de_session = cookies_poses(connecter(compte))[COOKIE_DE_RENOUVELLEMENT].value

    reponse = _renouveler(application, "caisse", identifiant_de_session)

    assert reponse.status_code == 204
    poses = _cookies_de_session(reponse)
    assert poses[COOKIE_DE_SESSION]["max-age"] == str(DUREE_DU_JETON)
    assert poses[COOKIE_DE_RENOUVELLEMENT].value == identifiant_de_session
    session = application("caisse").get(
        "/api/caisse/session", headers=par_cookie(**{COOKIE_DE_SESSION: poses[COOKIE_DE_SESSION].value})
    )
    assert (session.status_code, session.json()["sub"]) == (200, compte.sub)


def test_une_session_ne_se_renouvelle_que_sur_son_application(application, compte_de, connecter):
    identifiant_de_session = cookies_poses(connecter(compte_de("caissier")))[COOKIE_DE_RENOUVELLEMENT].value

    reponse = _renouveler(application, "soin", identifiant_de_session)

    assert reponse.status_code == 401
    _cookies_effaces(reponse)


@pytest.mark.parametrize("identifiant_de_session", [None, "inconnu"], ids=["sans cookie", "session inconnue"])
def test_le_renouvellement_sans_session_est_refuse(application, identifiant_de_session):
    reponse = _renouveler(application, "caisse", identifiant_de_session)

    assert reponse.status_code == 401
    _cookies_effaces(reponse)


def test_la_deconnexion_efface_les_deux_cookies_et_la_session_ne_se_renouvelle_plus(
    application, compte_de, connecter, formulaire
):
    identifiant_de_session = cookies_poses(connecter(compte_de("caissier")))[COOKIE_DE_RENOUVELLEMENT].value

    deconnexion = formulaire("caisse", "deconnexion", cookies={COOKIE_DE_RENOUVELLEMENT: identifiant_de_session})

    assert (deconnexion.status_code, deconnexion.headers.get("location")) == (303, "/connexion")
    _cookies_effaces(deconnexion)
    apres = _renouveler(application, "caisse", identifiant_de_session)
    assert apres.status_code == 401
    _cookies_effaces(apres)


def _porteur(jeton: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {jeton}"}


@pytest.mark.parametrize(
    "saisie",
    [
        pytest.param(lambda code: code, id="tel qu'imprimé"),
        pytest.param(lambda code: code.replace("-", ""), id="sans tiret"),
        pytest.param(lambda code: code.replace("-", " ").lower(), id="en minuscules, avec une espace"),
    ],
)
def test_un_citoyen_de_demonstration_se_connecte_avec_son_code(connecter_citoyen, citoyen_de_demonstration, saisie):
    citoyen = citoyen_de_demonstration

    reponse = connecter_citoyen(citoyen.npi, saisie(citoyen.code))

    assert (reponse.status_code, reponse.headers.get("location")) == (303, "/")
    poses = _cookies_de_session(reponse)
    assert poses[COOKIE_DE_SESSION]["max-age"] == str(DUREE_DU_JETON)
    assert poses[COOKIE_DE_RENOUVELLEMENT]["max-age"] == str(DUREE_MAXIMALE_D_UN_CITOYEN)


def test_deux_connexions_d_un_citoyen_ont_deux_identifiants_sans_rapport_avec_son_npi(
    application, connecter_citoyen, citoyen_de_demonstration
):
    citoyen = citoyen_de_demonstration

    jetons = [cookies_poses(connecter_citoyen(citoyen.npi, citoyen.code))[COOKIE_DE_SESSION].value for _ in range(2)]

    sessions = [application("citoyen").get("/api/citoyen/session", headers=_porteur(jeton)) for jeton in jetons]
    subs = [session.json()["sub"] for session in sessions]
    assert subs[0] != subs[1]
    assert [citoyen.npi in sub for sub in subs] == [False, False]


def test_npi_inconnu_mauvais_code_et_npi_mal_forme_recoivent_la_meme_reponse(
    connecter_citoyen, citoyen_de_demonstration
):
    citoyen = citoyen_de_demonstration
    # Aucun NPI du jeu ne commence par 0000008 : celui-ci n'a pas de code, et change à chaque passage.
    npi_inconnu = f"0000008{secrets.randbelow(10**6):06d}"

    reponses = [
        connecter_citoyen(npi_inconnu, citoyen.code),
        connecter_citoyen(citoyen.npi, "XXX-XXX"),
        connecter_citoyen(citoyen.npi[:-1], citoyen.code),
    ]
    # Remet à zéro le compteur d'échecs du NPI.
    assert connecter_citoyen(citoyen.npi, citoyen.code).status_code == 303

    for reponse in reponses:
        _refus(reponse, "identifiants")


def test_chaque_citoyen_liste_sur_la_page_de_connexion_se_connecte_avec_son_code(
    application, connecter_citoyen
):
    listes = application("citoyen").get("/api/identite/comptes-de-demonstration").json()

    # Un échec cite le rang du citoyen dans la liste, jamais son NPI.
    issues = [connecter_citoyen(citoyen["npi"], citoyen["code"]).headers.get("location") for citoyen in listes]

    assert listes
    assert [rang for rang, issue in enumerate(issues) if issue != "/"] == []


@pytest.mark.parametrize("acteur", ["soin", "caisse", "pharmacie"])
def test_un_citoyen_ne_se_connecte_que_sur_l_application_citoyen(connecter_citoyen, citoyen_de_demonstration, acteur):
    citoyen = citoyen_de_demonstration

    _refus(connecter_citoyen(citoyen.npi, citoyen.code, acteur=acteur), "application")


@pytest.fixture(scope="session")
def npi_sans_code_de_demonstration(jeu, citoyens) -> str:
    """Le NPI d'un patient réservé aux tests, sans code du jeu : la suite lui en émet."""
    avec_code = {c.npi for c in citoyens}
    return next(p["npi"] for p in jeu("patients")["patient"] if p.get("reserve_aux_tests") and p["npi"] not in avec_code)


@pytest.mark.parametrize("role", ["médecin", "infirmier"])
def test_un_soignant_obtient_un_code_carnet_qui_ouvre_le_carnet_et_remplace_le_precedent(
    application, jeton_de, connecter_citoyen, npi_sans_code_de_demonstration, role
):
    npi = npi_sans_code_de_demonstration

    def emettre() -> str:
        reponse = application("soin").post("/api/identite/codes-carnet", json={"npi": npi}, headers=_porteur(jeton_de(role)))
        assert reponse.status_code == 201
        assert set(reponse.json()) == {"code"}
        code: str = reponse.json()["code"]
        assert CODE_CARNET.fullmatch(code)
        return code

    ancien = emettre()
    assert connecter_citoyen(npi, ancien).headers.get("location") == "/"
    nouveau = emettre()

    _refus(connecter_citoyen(npi, ancien), "identifiants")
    assert connecter_citoyen(npi, nouveau).headers.get("location") == "/"


@pytest.mark.parametrize("role", ["caissier", "pharmacien", "officine", "citoyen"])
def test_seuls_les_soignants_obtiennent_un_code_carnet(application, jeton_de, npi_sans_code_de_demonstration, role):
    reponse = application(APPLICATION_DU_ROLE[role]).post(
        "/api/identite/codes-carnet", json={"npi": npi_sans_code_de_demonstration}, headers=_porteur(jeton_de(role))
    )

    assert reponse.status_code == 403


def test_un_code_carnet_exige_un_jeton(application, npi_sans_code_de_demonstration):
    reponse = application("soin").post("/api/identite/codes-carnet", json={"npi": npi_sans_code_de_demonstration})

    assert reponse.status_code == 401


@pytest.mark.parametrize(
    "corps",
    [{"npi": "123"}, {"npi": "000000900000A"}, {"npi": "00000090000031"}, {}],
    ids=["trop court", "une lettre", "trop long", "absent"],
)
def test_un_code_carnet_exige_un_npi_de_treize_chiffres(application, jeton_de, corps):
    reponse = application("soin").post("/api/identite/codes-carnet", json=corps, headers=_porteur(jeton_de("médecin")))

    assert reponse.status_code == 422


# Les verrous se testent sur des comptes et des NPI réservés aux tests : lancée en production, la suite
# ne verrouille jamais un compte de démonstration. Un compte verrouillé par un passage précédent, il y a
# moins de 15 minutes, l'est encore : ces tests le constatent sans ajouter d'échecs, qui compteraient
# contre l'adresse de la machine qui lance la suite.
ECHECS_AVANT_VERROU = 5
MAUVAIS_MOT_DE_PASSE = "pas-le-bon"


def _echouer_jusqu_au_verrou(essayer) -> None:
    """Cinq échecs, ou moins si le verrou d'un passage précédent tient encore."""
    for _ in range(ECHECS_AVANT_VERROU):
        reponse = essayer()
        assert reponse.headers.get("location") in ("/connexion?erreur=identifiants", "/connexion?erreur=verrouille")
        if reponse.headers["location"].endswith("verrouille"):
            return


def test_cinq_echecs_verrouillent_un_identifiant_meme_face_au_bon_mot_de_passe(comptes, connecter):
    compte = [c for c in comptes if c.reserve_aux_tests][0]

    _echouer_jusqu_au_verrou(lambda: connecter(compte, mot_de_passe=MAUVAIS_MOT_DE_PASSE))

    _refus(connecter(compte), "verrouille")


def test_cinq_echecs_verrouillent_un_npi_meme_face_au_bon_code(citoyens, connecter_citoyen):
    citoyen = [c for c in citoyens if c.reserve_aux_tests][0]

    _echouer_jusqu_au_verrou(lambda: connecter_citoyen(citoyen.npi, "XXX-XXX"))

    _refus(connecter_citoyen(citoyen.npi, citoyen.code), "verrouille")


def test_une_connexion_reussie_remet_les_echecs_a_zero(comptes, connecter):
    compte = [c for c in comptes if c.reserve_aux_tests][1]
    for _ in range(ECHECS_AVANT_VERROU - 1):
        _refus(connecter(compte, mot_de_passe=MAUVAIS_MOT_DE_PASSE), "identifiants")
    assert connecter(compte).headers.get("location") == "/"

    _refus(connecter(compte, mot_de_passe=MAUVAIS_MOT_DE_PASSE), "identifiants")

    # Sans remise à zéro, ce cinquième échec l'aurait verrouillé.
    assert connecter(compte).headers.get("location") == "/"


@pytest.fixture(scope="session")
def noms_des_structures(jeu) -> dict[str, str]:
    """Le nom de chaque établissement et de chaque officine du jeu, par identifiant."""
    return {s["id"]: s["nom"] for s in [*jeu("etablissements")["etablissement"], *jeu("officines")["officine"]]}


@pytest.mark.parametrize("role", ["médecin", "infirmier", "caissier", "pharmacien"])
def test_la_session_d_identite_nomme_l_agent_et_son_etablissement(
    application, jeu, compte_de, jeton_de, noms_des_structures, role
):
    compte = compte_de(role)
    agent = next(a for a in jeu("agents")["agent"] if a["id"] == compte.sub)

    reponse = application(compte.application).get("/api/identite/session", headers=_porteur(jeton_de(role)))

    assert reponse.status_code == 200
    assert reponse.json() == {
        "sub": compte.sub,
        "role": role,
        "etablissement": compte.etablissement,
        "nom": " ".join([*agent["prenoms"], agent["nom"]]),
        "nom_etablissement": noms_des_structures[compte.etablissement],
    }


def test_la_session_d_identite_nomme_l_officine(application, compte_de, jeton_de, noms_des_structures):
    compte = compte_de("officine")

    reponse = application("pharmacie").get("/api/identite/session", headers=_porteur(jeton_de("officine")))

    assert reponse.status_code == 200
    assert reponse.json() == {"sub": compte.sub, "role": "officine", "nom": noms_des_structures[compte.sub]}


def test_la_session_d_identite_ne_rend_jamais_le_npi_du_citoyen(application, jeton_de, citoyen_de_demonstration):
    reponse = application("citoyen").get("/api/identite/session", headers=_porteur(jeton_de("citoyen")))

    assert reponse.status_code == 200
    assert set(reponse.json()) == {"sub", "role"}
    assert reponse.json()["role"] == "citoyen"
    assert citoyen_de_demonstration.npi not in reponse.text


def test_la_session_d_identite_exige_un_jeton(application):
    assert application("soin").get("/api/identite/session").status_code == 401


def test_un_agent_a_deux_comptes_se_connecte_dans_l_etablissement_du_compte_choisi(application, comptes, connecter):
    # Le jeu donne à un médecin un compte dans deux établissements (donnees/agents.toml).
    subs = [c.sub for c in comptes]
    compte_a, compte_b = [c for c in comptes if subs.count(c.sub) == 2]

    sessions = [
        application("soin").get("/api/soin/session", headers=_porteur(cookies_poses(connecter(c))[COOKIE_DE_SESSION].value)).json()
        for c in (compte_a, compte_b)
    ]

    assert compte_a.sub == compte_b.sub
    assert [s["etablissement"] for s in sessions] == [compte_a.etablissement, compte_b.etablissement]
    assert compte_a.etablissement != compte_b.etablissement


@pytest.mark.parametrize("acteur", ["soin", "caisse", "pharmacie"])
def test_chaque_application_liste_ses_comptes_de_demonstration_sans_ceux_reserves_aux_tests(
    application, comptes, noms_des_structures, acteur
):
    reponse = application(acteur).get("/api/identite/comptes-de-demonstration")

    assert reponse.status_code == 200
    assert sorted(reponse.json(), key=lambda c: c["identifiant"]) == sorted(
        (
            {
                "identifiant": c.identifiant,
                "mot_de_passe": c.mot_de_passe,
                "role": c.role,
                "structure": noms_des_structures[c.etablissement or c.sub],
            }
            for c in comptes
            if c.application == acteur and not c.reserve_aux_tests
        ),
        key=lambda c: c["identifiant"],
    )


def test_l_application_citoyen_liste_ses_citoyens_de_demonstration_sans_ceux_reserves_aux_tests(
    application, citoyens
):
    reponse = application("citoyen").get("/api/identite/comptes-de-demonstration")

    assert reponse.status_code == 200
    assert reponse.json() == [
        {"npi": c.npi, "code": c.code, "role": "citoyen"} for c in citoyens if not c.reserve_aux_tests
    ]


def _cle_privee_neuve() -> str:
    """Une clé privée Ed25519 neuve, comme `JETON_CLE_PRIVEE` l'attend : le base64 de sa forme DER."""
    der = Ed25519PrivateKey.generate().private_bytes(Encoding.DER, PrivateFormat.PKCS8, NoEncryption())
    return base64.b64encode(der).decode()


@pytest.mark.parametrize(
    ("cle", "demarre"),
    [
        pytest.param("", False, id="sans clé"),
        pytest.param(CLE_PRIVEE_DE_DEVELOPPEMENT, False, id="avec la clé de développement"),
        pytest.param(_cle_privee_neuve(), True, id="avec une clé à lui"),
    ],
)
def test_hors_de_localhost_identite_ne_demarre_qu_avec_une_cle_a_lui(docker, cle, demarre):
    # L'image d'identite, sur un autre domaine que localhost ; son module se charge comme au démarrage.
    demarrage = docker(
        "compose", "run", "--rm", "--no-deps", "-T",
        "-e", "LAFIA_DOMAINE=lafia.exemple.org", "-e", f"JETON_CLE_PRIVEE={cle}",
        "identite", "python", "-c", "import identite.service",
    )

    assert (demarrage.returncode == 0) is demarre, demarrage.stderr[-500:]
    if not demarre:
        assert "JETON_CLE_PRIVEE" in demarrage.stderr
