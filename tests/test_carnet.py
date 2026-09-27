"""Carnet du citoyen (F3.6) : ce qu'il voit de son dossier, sur son seul NPI, et la trace qu'il en laisse.

Le carnet vécu et le carnet à payer sont ceux de l'histoire clinique de démonstration
(donnees/src/donnees/historique.py) : leurs identifiants sont fixes, leurs dates relatives au chargement.
"""

import pytest

from conftest import jeton_pose
from test_soin import page_png

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


CARNET_VIDE = "0000002316294"


def test_ma_sante_dit_le_groupe_sanguin_les_antecedents_et_les_traitements_au_long_cours(
    application, jeton_du_citoyen
):
    client = application("citoyen")

    vecu = client.get("/api/citoyen/ma-sante", headers={"Authorization": f"Bearer {jeton_du_citoyen(CARNET_VECU)}"})
    vide = client.get("/api/citoyen/ma-sante", headers={"Authorization": f"Bearer {jeton_du_citoyen(CARNET_VIDE)}"})

    assert (vecu.status_code, vide.status_code) == (200, 200)
    sante = vecu.json()
    assert sante["groupe_sanguin"] == "O+"
    assert any("Hypertension" in a["libelle"] and a["actif"] for a in sante["antecedents"])
    assert {"lien": "Votre mère", "libelle": "Diabète", "origine": "declaration"} in sante["familiaux"]
    assert sante["origine_du_groupe_sanguin"] == "declaration"
    assert any("Amlodipine" in t["libelle"] and t["moments"] == ["matin"] for t in sante["traitements"])
    assert CARNET_VECU not in vecu.text
    assert vide.json() == {
        "groupe_sanguin": None,
        "origine_du_groupe_sanguin": None,
        "allergies": [],
        "antecedents": [],
        "familiaux": [],
        "traitements": [],
    }


def test_un_antecedent_n_est_jamais_le_diagnostic_d_une_visite_et_chaque_ligne_dit_son_unite(
    application, jeton_du_citoyen
):
    client = application("citoyen")
    entetes = {"Authorization": f"Bearer {jeton_du_citoyen(CARNET_VECU)}"}

    cas = [client.get(f"/api/citoyen/cas/{c['id']}", headers=entetes).json() for c in
           client.get("/api/citoyen/cas", headers=entetes).json()]
    ordonnances = client.get("/api/citoyen/ordonnances", headers=entetes).json()

    diagnostics = [d for c in cas for v in c["visites_lues"] for d in v["diagnostics"]]
    assert diagnostics and not any("Hypertension" in d or "Appendicectomie" in d for d in diagnostics)
    lignes = [ligne for o in ordonnances if o["numero"] in ("ORD-7K4-M2P", "ORD-5PW-8RB") for ligne in o["lignes"]]
    assert all(ligne["unite"] and not ligne["arret_allergie"] for ligne in lignes)
    assert "gélule" in {ligne["unite"] for ligne in lignes}


def test_le_citoyen_voit_ses_documents_et_jamais_ceux_d_un_autre(
    application, jeton_de, jeton_du_citoyen, jeu, connecter_citoyen
):
    # Un médecin ajoute au dossier un papier que le patient a apporté, pendant un cas qu'il ouvre et clôt.
    soin = application("soin")
    medecin = {"Authorization": f"Bearer {jeton_de('médecin')}"}
    patient_id = soin.post("/api/soin/recherche", json={"npi": CARNET_VECU}, headers=medecin).json()["patient_id"]
    cas = soin.post(f"/api/soin/patients/{patient_id}/cas", json={"motif": "Anciens papiers"}, headers=medecin)
    assert cas.status_code == 201
    page = page_png()
    ajoute = soin.post(
        f"/api/soin/patients/{patient_id}/documents",
        data={"type": "resultat-analyse", "annee": "2021", "lisibilite": "partiel"},
        files=[("pages", ("analyse.png", page, "image/png"))],
        headers=medecin,
    )
    soin.post(f"/api/soin/cas/{cas.json()['cas_id']}/cloture", headers=medecin)
    assert ajoute.status_code == 201, ajoute.text
    document_id = ajoute.json()["document_id"]

    client = application("citoyen")
    entetes = {"Authorization": f"Bearer {jeton_du_citoyen(CARNET_VECU)}"}
    mes_documents = client.get("/api/citoyen/documents", headers=entetes)
    assert mes_documents.status_code == 200, mes_documents.text
    (document,) = [d for d in mes_documents.json() if d["id"] == document_id]
    assert (document["type"], document["annee"], document["pages"], document["lisibilite"], document["origine"]) == (
        "resultat-analyse", "2021", 1, "partiel", "numerisation"
    )
    lue = client.get(f"/api/citoyen/documents/{document_id}/pages/1", headers=entetes)
    assert lue.status_code == 200 and lue.content == page
    assert CARNET_VECU not in mes_documents.text

    # Un autre citoyen : ce Document n'existe pas pour lui.
    autre = [p["npi"] for p in jeu("patients")["patient"] if p.get("reserve_aux_tests")][-1]
    code = soin.post("/api/identite/codes-carnet", json={"npi": autre}, headers=medecin).json()["code"]
    son_jeton = {"Authorization": f"Bearer {jeton_pose(connecter_citoyen(autre, code))}"}
    assert client.get(f"/api/citoyen/documents/{document_id}/pages/1", headers=son_jeton).status_code == 404
    assert document_id not in {d["id"] for d in client.get("/api/citoyen/documents", headers=son_jeton).json()}


def _citoyen_reserve_aux_tests(application, jeton_de, jeu, connecter_citoyen, rang: int) -> tuple[str, dict[str, str]]:
    """Un patient réservé aux tests, son NPI et l'en-tête de son carnet, par un code qu'un médecin lui émet."""
    npi = [p["npi"] for p in jeu("patients")["patient"] if p.get("reserve_aux_tests")][rang]
    code = application("soin").post(
        "/api/identite/codes-carnet", json={"npi": npi}, headers={"Authorization": f"Bearer {jeton_de('médecin')}"}
    ).json()["code"]
    return npi, {"Authorization": f"Bearer {jeton_pose(connecter_citoyen(npi, code))}"}


def test_ma_sante_dit_d_ou_vient_chaque_information(application, jeton_de, jeu, connecter_citoyen):
    # Un antécédent saisi par un médecin, sans Document : une déclaration du patient (ADR 0007).
    npi, carnet = _citoyen_reserve_aux_tests(application, jeton_de, jeu, connecter_citoyen, -1)
    soin = application("soin")
    medecin = {"Authorization": f"Bearer {jeton_de('médecin')}"}
    patient_id = soin.post("/api/soin/recherche", json={"npi": npi}, headers=medecin).json()["patient_id"]
    cas = soin.post(f"/api/soin/patients/{patient_id}/cas", json={"motif": "Bilan"}, headers=medecin)
    assert cas.status_code == 201
    ajoute = soin.post(
        f"/api/soin/patients/{patient_id}/antecedents",
        json={"type": "chirurgical", "libelle": "Césarienne", "depuis": "2015"},
        headers=medecin,
    )
    soin.post(f"/api/soin/cas/{cas.json()['cas_id']}/cloture", headers=medecin)
    assert ajoute.status_code == 201, ajoute.text

    sante = application("citoyen").get("/api/citoyen/ma-sante", headers=carnet)

    assert sante.status_code == 200, sante.text
    assert {"libelle": "Césarienne", "origine": "declaration"}.items() <= next(
        a for a in sante.json()["antecedents"] if a["libelle"] == "Césarienne"
    ).items()
    assert npi not in sante.text


def _agent_de_numerisation(comptes, connecter) -> dict[str, str]:
    compte = next(
        c for c in comptes if c.role == "agent de numérisation" and c.etablissement == "cnhu-hkm" and not c.reserve_aux_tests
    )
    return {"Authorization": f"Bearer {jeton_pose(connecter(compte))}"}


def test_le_journal_dit_un_depot_par_ligne_et_ce_qu_il_a_ajoute(
    application, jeton_de, jeu, comptes, connecter, connecter_citoyen
):
    npi, carnet = _citoyen_reserve_aux_tests(application, jeton_de, jeu, connecter_citoyen, -1)
    numerisation = application("numerisation")
    agent = _agent_de_numerisation(comptes, connecter)

    # Un premier Dépôt, clos sans rien : le dossier a été consulté, rien n'y a été ajouté.
    vide = numerisation.post("/api/numerisation/depots", json={"npi": npi, "piece": "cni"}, headers=agent)
    assert vide.status_code == 201, vide.text
    assert numerisation.post(f"/api/numerisation/depots/{vide.json()['depot_id']}/cloture", headers=agent).status_code == 200
    # Un second, du même agent, avec un Document.
    plein = numerisation.post("/api/numerisation/depots", json={"npi": npi, "piece": "cni"}, headers=agent)
    depot = plein.json()["depot_id"]
    depose = numerisation.post(
        f"/api/numerisation/depots/{depot}/documents",
        data={"type": "carnet", "annee": "2018", "lisibilite": "lisible"},
        files=[("pages", ("page.png", page_png(), "image/png"))],
        headers=agent,
    )
    assert depose.status_code == 201, depose.text
    assert numerisation.post(f"/api/numerisation/depots/{depot}/cloture", headers=agent).status_code == 200

    journal = application("citoyen").get("/api/citoyen/acces", headers=carnet)

    assert journal.status_code == 200, journal.text
    au_guichet = [a for a in journal.json() if a["service"] == "numerisation"]
    # Deux Dépôts, deux lignes : le même agent ne les fond pas en une. Les deux lignes de ce passage
    # sont les deux plus récentes ; leur ordre entre elles ne compte pas.
    recents = au_guichet[:2]
    avec_documents = [a for a in recents if a["depot"]]
    sans_rien = [a for a in recents if not a["depot"]]
    assert len(avec_documents) == len(sans_rien) == 1, recents
    assert avec_documents[0]["motif"].startswith("Vos papiers ont été numérisés")
    assert sans_rien[0]["motif"] == "Dossier consulté au guichet de numérisation, rien n'a été ajouté"
    assert npi not in journal.text


# Le carnet papier de patient-001, numérisé, relu et contrôlé (historique.py, F6.6).
DOCUMENT_TRANSCRIT = "hist-a-carnet-papier"


def test_un_papier_relu_se_lit_en_texte_et_par_etablissement_et_jamais_par_un_autre(
    application, jeton_de, jeton_du_citoyen, jeu, connecter_citoyen
):
    client = application("citoyen")
    entetes = {"Authorization": f"Bearer {jeton_du_citoyen(CARNET_VECU)}"}

    (document,) = [d for d in client.get("/api/citoyen/documents", headers=entetes).json() if d["id"] == DOCUMENT_TRANSCRIT]
    assert document["transcription"] is True and document["papier_abime"]
    texte = client.get(f"/api/citoyen/documents/{DOCUMENT_TRANSCRIT}/transcription", headers=entetes)
    assert texte.status_code == 200, texte.text
    assert texte.json()["pages"] == 4 and texte.json()["relue_le"]
    assert "## consultation · 2015-06-02 · CS Kpanroun · p. 1" in texte.json()["markdown"]

    par_etablissement = client.get("/api/citoyen/par-etablissement", headers=entetes)
    assert par_etablissement.status_code == 200, par_etablissement.text
    groupes = {e["etablissement"]: e["volets"] for e in par_etablissement.json()}
    assert {"CS Kpanroun", "CHD Ouémé"} <= set(groupes)
    kpanroun = [v for v in groupes["CS Kpanroun"] if v["document_id"] == DOCUMENT_TRANSCRIT]
    assert [(v["type"], v["date"], v["pages"]) for v in kpanroun] == [
        ("consultation", "2015-06-02", [1]), ("consultation", "2019-03-14", [4])
    ]
    assert {v["type"] for v in groupes["CHD Ouémé"] if v["document_id"] == DOCUMENT_TRANSCRIT} == {"hospitalisation", "analyse"}
    for volets in groupes.values():
        dates = [v["date"] for v in volets if v["date"]]
        assert dates == sorted(dates)
    # Le NPI ne quitte jamais le service.
    assert CARNET_VECU not in par_etablissement.text and CARNET_VECU not in texte.text

    # Un autre citoyen : ce papier et son texte n'existent pas pour lui.
    _, autre = _citoyen_reserve_aux_tests(application, jeton_de, jeu, connecter_citoyen, -2)
    assert client.get(f"/api/citoyen/documents/{DOCUMENT_TRANSCRIT}/transcription", headers=autre).status_code == 404
    siens = client.get("/api/citoyen/par-etablissement", headers=autre)
    assert siens.status_code == 200
    assert DOCUMENT_TRANSCRIT not in {v["document_id"] for e in siens.json() for v in e["volets"]}
