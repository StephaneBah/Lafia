"""Carnet du citoyen (F3.6) : ce qu'il voit de son dossier, sur son seul NPI, et la trace qu'il en laisse.

Le carnet vécu et le carnet à payer sont ceux de l'histoire clinique de démonstration
(donnees/src/donnees/historique.py) : leurs identifiants sont fixes, leurs dates relatives au chargement.
"""

import pytest

from conftest import jeton_pose

CARNET_VECU = "0000001204815"
CAS_EN_COURS = "hist-a-cas-ira"


@pytest.fixture(scope="module")
def jeton_du_citoyen(citoyens, connecter_citoyen):
    """Le jeton d'un citoyen de démonstration, par son NPI : `jeton_du_citoyen(CARNET_VECU)`."""
    jetons: dict[str, str] = {}

    def jeton(npi: str) -> str:
        if npi not in jetons:
            citoyen = next(c for c in citoyens if c.npi == npi)
            jetons[npi] = jeton_pose(connecter_citoyen(citoyen.npi, citoyen.code))
        return jetons[npi]

    return jeton


def test_le_citoyen_voit_ses_cas_son_ordonnance_son_traitement_et_qui_a_ouvert_son_dossier(
    application, jeton_du_citoyen
):
    client = application("citoyen")
    entetes = {"Authorization": f"Bearer {jeton_du_citoyen(CARNET_VECU)}"}

    reponses = {chemin: client.get(f"/api/citoyen{chemin}", headers=entetes) for chemin in
                ["/carnet", "/cas", f"/cas/{CAS_EN_COURS}", "/ordonnances", "/traitement", "/acces"]}

    assert {chemin: r.status_code for chemin, r in reponses.items()} == dict.fromkeys(reponses, 200)
    accueil = reponses["/carnet"].json()
    assert accueil["cas_en_cours"] >= 1 and accueil["prenom"]
    assert CAS_EN_COURS in {cas["id"] for cas in reponses["/cas"].json()}
    visite = reponses[f"/cas/{CAS_EN_COURS}"].json()["visites_lues"][0]
    assert visite["mesures"] and visite["diagnostics"] and visite["soignant"]
    ordonnances = {o["numero"]: o for o in reponses["/ordonnances"].json()}
    assert {"ORD-7K4-M2P", "ORD-5PW-8RB"} <= set(ordonnances)
    assert {ligne["statut"] for ligne in ordonnances["ORD-5PW-8RB"]["lignes"]} == {"retire"}
    assert any(reponses["/traitement"].json()["moments"].values())
    urgences = [a for a in reponses["/acces"].json() if a["urgence"]]
    assert urgences and urgences[0]["raison"]
    # Le NPI ne quitte jamais le service.
    assert [chemin for chemin, r in reponses.items() if CARNET_VECU in r.text] == []


def test_chaque_lecture_du_carnet_laisse_un_acces_au_nom_du_patient(application, jeton_du_citoyen, noyau):
    application("citoyen").get("/api/citoyen/carnet", headers={"Authorization": f"Bearer {jeton_du_citoyen(CARNET_VECU)}"})

    (reponse,) = noyau(["AuditEvent?entity=Patient/patient-001&_sort=-date&_count=1"])

    dernier = reponse.ressource["entry"][0]["resource"]
    assert dernier["agent"][0]["who"]["reference"] == "Patient/patient-001"
    assert dernier["agent"][0]["purposeOfUse"][0]["coding"][0]["code"] == "citoyen"


def test_un_citoyen_ne_lit_pas_le_cas_d_un_autre_et_un_agent_n_ouvre_aucun_carnet(
    application, jeton_de, jeu, connecter_citoyen
):
    client = application("citoyen")
    # Un autre citoyen : un patient réservé aux tests, à qui un médecin émet un code. Les codes publics du
    # jeu, eux, peuvent avoir été remplacés par un soignant pendant une démonstration.
    autre = [p["npi"] for p in jeu("patients")["patient"] if p.get("reserve_aux_tests")][-1]
    code = application("soin").post(
        "/api/identite/codes-carnet", json={"npi": autre}, headers={"Authorization": f"Bearer {jeton_de('médecin')}"}
    ).json()["code"]

    cas_d_un_autre = client.get(
        f"/api/citoyen/cas/{CAS_EN_COURS}",
        headers={"Authorization": f"Bearer {jeton_pose(connecter_citoyen(autre, code))}"},
    )
    agent = client.get("/api/citoyen/carnet", headers={"Authorization": f"Bearer {jeton_de('médecin')}"})

    assert (cas_d_un_autre.status_code, agent.status_code) == (404, 403)
