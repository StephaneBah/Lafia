"""Le service relecture (F6, ADR 0009, 0010) : un Document ajouté pendant une visite entre au pool ; un agent
de relecture d'un autre département le reçoit dans sa semaine, sans rien qui dise de qui il est ; à
l'ouverture, l'Extraction de démonstration en donne un brouillon de Transcription en volets ; il le corrige,
coche chaque volet et confirme ; un second agent de relecture, jamais le premier, le contrôle, le renvoie
avec une note, puis l'accepte : la Transcription est relue. Un médecin valide alors une proposition, qui
entre au dossier avec l'origine `extraction`.

Le pool sert les plus vieux papiers d'abord : les Documents de ce test sont datés de 1900, qu'aucun autre
test n'emploie, pour passer devant ceux que la suite dépose ailleurs. L'agent prend une Relecture de 1900
de sa semaine et clôt les autres comme inutilisables : toutes viennent de ce test, au dossier du même
patient, et une Relecture close libère sa place pour le passage suivant.
"""

import base64
import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from conftest import Compte, jeton_pose
from test_soin import page_png

# Un patient du jeu de démonstration, celui des tests de soin.
NPI = "0000001317462"
ANNEE_DU_PAPIER = "1900"
PAGES = 2
RELECTURE = "/api/relecture"


def _porteur(jeton: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {jeton}"}


@pytest.fixture(scope="module")
def second_relecteur(comptes: list[Compte], connecter: Callable[..., httpx.Response]) -> Compte:
    """Le second agent de relecture de démonstration : le contrôleur des relectures du premier."""
    relecteurs = [c for c in comptes if c.role == "agent de relecture" and not c.reserve_aux_tests]
    assert len(relecteurs) >= 2, relecteurs
    return relecteurs[1]


def _ajouter_un_document(soin: httpx.Client, medecin: dict[str, str], patient_id: str) -> None:
    ajoute = soin.post(
        f"/api/soin/patients/{patient_id}/documents",
        data={"type": "carnet", "annee": ANNEE_DU_PAPIER, "lisibilite": "lisible"},
        files=[("pages", (f"page-{n}.png", page_png(), "image/png")) for n in range(1, PAGES + 1)],
        headers=medecin,
    )
    assert ajoute.status_code == 201, ajoute.text


def _ouvrir(relecture: httpx.Client, tache_id: str, qui: dict[str, str]) -> tuple[dict[str, Any], str]:
    vue = relecture.get(f"{RELECTURE}/taches/{tache_id}", headers=qui)
    assert vue.status_code == 200, vue.text
    return vue.json(), vue.headers["ETag"]


def _enregistrer(relecture: httpx.Client, tache_id: str, qui: dict[str, str], markdown: str, version: str) -> str:
    enregistre = relecture.put(
        f"{RELECTURE}/taches/{tache_id}/transcription", json={"markdown": markdown}, headers={**qui, "If-Match": version}
    )
    assert enregistre.status_code == 200, enregistre.text
    return enregistre.headers["ETag"]


def _confirmer(relecture: httpx.Client, tache_id: str, qui: dict[str, str], volets: list[int], resume: str) -> httpx.Response:
    return relecture.post(f"{RELECTURE}/taches/{tache_id}/confirmation", json={"volets_verifies": volets, "resume": resume}, headers=qui)


def test_une_transcription_est_relue_controlee_puis_ses_faits_valides(
    application, jeton_de, compte_de, second_relecteur, connecter, jeu, request
):
    soin = application("soin")
    relecture = application("relecture")
    medecin = _porteur(jeton_de("médecin"))
    agent_a = _porteur(jeton_de("agent de relecture"))
    agent_b = _porteur(jeton_pose(connecter(second_relecteur)))
    # Les deux agents de relecture travaillent à Parakou et à Kpanroun ; le médecin, à Cotonou.
    departements = {e["id"]: e["departement"] for e in jeu("etablissements")["etablissement"]}
    chez_le_medecin = departements[compte_de("médecin").etablissement]
    assert chez_le_medecin not in {departements[compte_de("agent de relecture").etablissement], departements[second_relecteur.etablissement]}

    trouve = soin.post("/api/soin/recherche", json={"npi": NPI}, headers=medecin)
    assert trouve.status_code == 200, trouve.text
    patient_id = trouve.json()["patient_id"]
    cas = soin.post(f"/api/soin/patients/{patient_id}/cas", json={"motif": "Anciens papiers à relire"}, headers=medecin)
    assert cas.status_code == 201, cas.text
    nom = soin.get(f"/api/soin/patients/{patient_id}", headers=medecin).json()["patient"]["nom"]
    revelateurs = (NPI, nom, patient_id)
    # Deux papiers : l'un sera relu, l'autre clos comme inutilisable.
    _ajouter_un_document(soin, medecin, patient_id)
    _ajouter_un_document(soin, medecin, patient_id)

    # La semaine de A : les papiers de 1900 y sont, à relire, sans rien qui dise de qui ils sont.
    semaine = relecture.get(f"{RELECTURE}/taches", headers=agent_a)
    assert semaine.status_code == 200, semaine.text
    a_relire = [
        t for t in semaine.json()
        if t["etape"] == "relecture" and t["statut"] != "terminee" and t["document"]["annee"] == ANNEE_DU_PAPIER
    ]
    assert len(a_relire) >= 2, semaine.json()
    tache_id = a_relire[0]["id"]

    # Les autres : closes sans Transcription ; une seconde fois, la Tâche n'est plus à relire.
    for tache in a_relire[1:]:
        close = relecture.post(f"{RELECTURE}/taches/{tache['id']}/inutilisable", json={"raison": "doublon"}, headers=agent_a)
        assert close.status_code == 200, close.text
        assert close.json()["statut"] == "terminee"
    assert relecture.post(f"{RELECTURE}/taches/{a_relire[1]['id']}/inutilisable", json={"raison": "doublon"}, headers=agent_a).status_code == 409

    # À l'ouverture : le brouillon de l'Extraction de démonstration, en volets qui renvoient aux pages.
    vue, version = _ouvrir(relecture, tache_id, agent_a)
    assert (vue["etape"], vue["document"]["type"], vue["document"]["pages"]) == ("relecture", "carnet", PAGES)
    assert vue["modele"] == {"nom": "demonstration", "version": "0", "demonstration": True}
    assert vue["volets"][0]["type"] == "note" and vue["erreurs"] == []
    assert all(1 <= p <= PAGES for v in vue["volets"] for p in v["pages"])
    assert "Lecture de démonstration" in vue["markdown"]
    for revelateur in revelateurs:
        assert revelateur not in json.dumps(vue)
    page = relecture.get(f"{RELECTURE}/taches/{tache_id}/pages/1", headers=agent_a)
    assert page.status_code == 200 and page.content == page_png()

    # Le brouillon corrigé : sans If-Match, refusé ; sur une version passée, en conflit ; puis enregistré.
    corrige = vue["markdown"].rstrip("\n") + "\nPrécision du relecteur : la fin de la page est pâlie.\n"
    sans_version = relecture.put(f"{RELECTURE}/taches/{tache_id}/transcription", json={"markdown": corrige}, headers=agent_a)
    assert sans_version.status_code == 428
    perimee = relecture.put(f"{RELECTURE}/taches/{tache_id}/transcription", json={"markdown": corrige}, headers={**agent_a, "If-Match": 'W/"0"'})
    assert perimee.status_code == 409
    version = _enregistrer(relecture, tache_id, agent_a, corrige, version)
    tous = [v["rang"] for v in vue["volets"]]

    # La confirmation refuse un volet non coché, puis un titre de volet hors format.
    refus = _confirmer(relecture, tache_id, agent_a, tous[:-1], "Fin de page précisée.")
    assert refus.status_code == 422, refus.text
    assert refus.json()["detail"]["volets_non_verifies"] == [tous[-1]]
    mal_forme = corrige.replace("## note · ? · ? · p. 1", "## note sans ses repères", 1)
    version = _enregistrer(relecture, tache_id, agent_a, mal_forme, version)
    refus = _confirmer(relecture, tache_id, agent_a, tous, "Fin de page précisée.")
    assert refus.status_code == 422, refus.text
    assert refus.json()["detail"]["erreurs"], refus.text
    version = _enregistrer(relecture, tache_id, agent_a, corrige, version)

    # Confirmée : une version de la Transcription, et un Contrôle pour un autre que A.
    confirmee = _confirmer(relecture, tache_id, agent_a, tous, "Fin de page précisée.")
    assert confirmee.status_code == 200, confirmee.text
    assert confirmee.json()["relue"] is False
    controle_id = confirmee.json()["controle"]
    assert controle_id
    assert controle_id not in [t["id"] for t in relecture.get(f"{RELECTURE}/taches", headers=agent_a).json()]
    assert relecture.get(f"{RELECTURE}/taches/{controle_id}", headers=agent_a).status_code == 403
    assert relecture.post(f"{RELECTURE}/taches/{controle_id}/controle", json={"decision": "accepter"}, headers=agent_a).status_code == 403

    # B le reçoit, lit la Transcription confirmée et le résumé de A, et la renvoie avec une note.
    semaine_b = relecture.get(f"{RELECTURE}/taches", headers=agent_b)
    assert semaine_b.status_code == 200, semaine_b.text
    assert controle_id in [t["id"] for t in semaine_b.json() if t["etape"] == "controle"], semaine_b.json()
    a_controler, _ = _ouvrir(relecture, controle_id, agent_b)
    assert a_controler["etape"] == "controle"
    assert "pâlie" in a_controler["markdown"] and a_controler["resume"] == "Fin de page précisée."
    for revelateur in revelateurs:
        assert revelateur not in json.dumps(a_controler)
    assert relecture.post(f"{RELECTURE}/taches/{controle_id}/controle", json={"decision": "renvoyer"}, headers=agent_b).status_code == 422
    note = "Page 2 : le volet d'analyse porte deux résultats, un seul est transcrit."
    renvoi = relecture.post(f"{RELECTURE}/taches/{controle_id}/controle", json={"decision": "renvoyer", "note": note}, headers=agent_b)
    assert renvoi.status_code == 200, renvoi.text

    # A la retrouve à faire, avec la note, son brouillon gardé ; il la confirme de nouveau.
    revenue = [t for t in relecture.get(f"{RELECTURE}/taches", headers=agent_a).json() if t["id"] == tache_id]
    assert revenue and revenue[0]["renvoyee"] is True and revenue[0]["statut"] == "a-faire", revenue
    vue, version = _ouvrir(relecture, tache_id, agent_a)
    assert note in [n["texte"] for n in vue["notes_de_controle"]]
    assert "pâlie" in vue["markdown"]
    confirmee = _confirmer(relecture, tache_id, agent_a, [v["rang"] for v in vue["volets"]], "Second résultat vérifié.")
    assert confirmee.status_code == 200, confirmee.text
    second_controle = confirmee.json()["controle"]
    preliminaire = confirmee.json()["transcription"]

    # B l'accepte : la Transcription est relue.
    assert second_controle in [t["id"] for t in relecture.get(f"{RELECTURE}/taches", headers=agent_b).json()]
    acceptee = relecture.post(f"{RELECTURE}/taches/{second_controle}/controle", json={"decision": "accepter"}, headers=agent_b)
    assert acceptee.status_code == 200, acceptee.text
    relue = acceptee.json()["transcription"]
    validation_id = acceptee.json()["validation"]
    assert relue and validation_id
    assert relecture.post(f"{RELECTURE}/taches/{second_controle}/controle", json={"decision": "accepter"}, headers=agent_b).status_code == 409

    # Le suivi de chacun.
    suivi_a = relecture.get(f"{RELECTURE}/suivi", headers=agent_a).json()
    assert suivi_a["semaine"]["confirmees"] >= 1 and suivi_a["semaine"]["renvoyees"] >= 1, suivi_a
    assert (tache_id, "relue") in [(e["id"], e["issue"]) for e in suivi_a["historique"]]
    suivi_b = relecture.get(f"{RELECTURE}/suivi", headers=agent_b).json()
    assert suivi_b["semaine"]["controlees"] >= 2, suivi_b
    assert relecture.get(f"{RELECTURE}/suivi", headers=medecin).status_code == 403

    # Le médecin prend la validation : les propositions de l'Extraction, à côté de la Transcription relue.
    lue = relecture.get(f"{RELECTURE}/taches/{validation_id}", headers=medecin)
    assert lue.status_code == 200, lue.text
    assert (lue.json()["etape"], lue.json()["statut"]) == ("validation", "en-cours")
    assert "pâlie" in lue.json()["markdown"]
    for revelateur in revelateurs:
        assert revelateur not in lue.text
    types = {p["type"]: p for p in lue.json()["propositions"]}
    assert set(types) == {"Condition", "AllergyIntolerance", "Observation"}
    # L'agent de relecture ne valide pas ; une proposition inconnue est refusée.
    assert relecture.post(f"{RELECTURE}/taches/{validation_id}/validation", json={"propositions": []}, headers=agent_a).status_code == 403
    inconnue = relecture.post(
        f"{RELECTURE}/taches/{validation_id}/validation", json={"propositions": [{"id": "p99", "decision": "accepter"}]}, headers=medecin
    )
    assert inconnue.status_code == 422
    validee = relecture.post(
        f"{RELECTURE}/taches/{validation_id}/validation",
        json={"propositions": [{"id": types["Condition"]["id"], "decision": "accepter"}]},
        headers=medecin,
    )
    assert validee.status_code == 200, validee.text
    ((entree),) = validee.json()["entrees"]
    bandeau = soin.get(f"/api/soin/patients/{patient_id}", headers=medecin).json()
    (antecedent,) = [a for a in bandeau["antecedents"] if a["id"] == entree["id"]]
    assert (antecedent["libelle"], antecedent["origine"]) == ("Paludisme", "extraction")
    soin.post(f"/api/soin/cas/{cas.json()['cas_id']}/cloture", headers=medecin)

    # Dans le noyau : la version relue transforme le scan et remplace la préliminaire, désormais remplacée ;
    # son Markdown est celui de A ; le Contrôle de B en est la Provenance.
    noyau = request.getfixturevalue("noyau")
    finale, ancienne, provenances = noyau(
        [f"DocumentReference/{relue}", f"DocumentReference/{preliminaire}", f"Provenance?target=DocumentReference/{relue}"]
    )
    document = finale.ressource
    assert document["type"]["coding"][0]["code"] == "transcription"
    assert (document["status"], document["docStatus"]) == ("current", "final")
    relations = {r["code"]: r["target"]["reference"] for r in document["relatesTo"]}
    assert relations["transforms"].startswith("DocumentReference/")
    assert relations["replaces"] == f"DocumentReference/{preliminaire}"
    assert "extraction" in [t["code"] for t in document["meta"]["tag"]]
    assert (ancienne.ressource["status"], ancienne.ressource["docStatus"]) == ("superseded", "preliminary")
    (binaire,) = noyau([document["content"][0]["attachment"]["url"]])
    assert "pâlie" in base64.b64decode(binaire.ressource["data"]).decode()
    activites = [e["resource"]["activity"]["coding"][0]["code"] for e in provenances.ressource.get("entry", [])]
    assert activites == ["controle"]


# Joint extraction depuis relecture, seul conteneur qui le peut, et lit chaque réponse au contrat de
# `commun.extraction` : la page, en base64, arrive sur l'entrée standard. Chaque brouillon de Transcription
# est lu par `commun.transcription`, contre le nombre de pages envoyées.
APPEL_D_EXTRACTION = """
import json, os, sys, httpx
from commun.extraction import DemandeDExtraction, Extraction
from commun.transcription import lire
page = sys.stdin.read()
reponses = {}
for type_ in sys.argv[1:]:
    for pages in (1, 6):
        demande = DemandeDExtraction(document_id="contrat", type_de_document=type_, pages=[{"format": "image/png", "octets": page}] * pages)
        reponse = httpx.post(os.environ["EXTRACTION_URL"] + "/extraire", json=demande.model_dump(), timeout=30)
        reponse.raise_for_status()
        extraction = Extraction.model_validate(reponse.json())
        lue = lire(extraction.transcription, pages)
        reponses[f"{type_}:{pages}"] = {
            **extraction.model_dump(),
            "erreurs": list(lue.erreurs),
            "volets": [v.type for v in lue.volets],
        }
json.dump(reponses, sys.stdout)
"""
TYPES_DE_DOCUMENT = ["carnet", "compte-rendu", "resultat-analyse", "ordonnance", "imagerie", "certificat", "autre"]


def _concepts(valeur):
    """Chaque CodeableConcept d'une ressource, à toute profondeur."""
    if isinstance(valeur, dict):
        if "coding" in valeur:
            yield valeur
        for enfant in valeur.values():
            yield from _concepts(enfant)
    elif isinstance(valeur, list):
        for enfant in valeur:
            yield from _concepts(enfant)


def test_l_extraction_de_demonstration_repond_au_contrat(docker):
    appel = docker(
        "compose", "exec", "-T", "relecture", "python", "-c", APPEL_D_EXTRACTION, *TYPES_DE_DOCUMENT,
        entree=base64.b64encode(page_png()).decode(),
    )
    assert appel.returncode == 0, appel.stderr

    reponses = json.loads(appel.stdout)
    for cle, extraction in reponses.items():
        assert extraction["modele"] == {"nom": "demonstration", "version": "0"}, cle
        assert "démonstration" in extraction["texte"]
        # Le brouillon suit l'ADR 0010, ne renvoie qu'à des pages envoyées, et se dit de démonstration.
        assert extraction["erreurs"] == [], (cle, extraction["erreurs"])
        assert extraction["volets"][0] == "note", cle
        assert "Lecture de démonstration" in extraction["transcription"]
        assert "](page:" in extraction["transcription"]
        assert ("illisible" in extraction["volets"]) == cle.endswith(":6"), cle
        for proposition in extraction["propositions"]:
            ressource = proposition["ressource"]
            assert ressource["resourceType"] in {"Observation", "Condition", "AllergyIntolerance", "MedicationStatement"}
            # Un brouillon : ni identifiant, ni sujet, ni auteur ; le soignant les donne à la validation.
            assert not {"id", "subject", "patient", "recorder", "performer", "informationSource"} & set(ressource)
            assert 0.6 <= proposition["confiance"] <= 0.9
            assert proposition["extrait"] in extraction["texte"]
            for concept in _concepts(ressource):
                assert concept.get("text"), concept
                assert all(c.get("display") for c in concept["coding"]), concept
    carnet = reponses["carnet:1"]
    assert [p["ressource"]["resourceType"] for p in carnet["propositions"]] == ["Condition", "AllergyIntolerance", "Observation"]
    # Un résultat d'analyse : un tableau dans le brouillon, l'hémoglobine en proposition.
    assert "| Hémoglobine | 10,2 | g/dL |" in reponses["resultat-analyse:1"]["transcription"]
    (hemoglobine,) = reponses["resultat-analyse:1"]["propositions"]
    assert hemoglobine["ressource"]["code"]["coding"][0]["code"] == "718-7"
    assert reponses["imagerie:1"]["propositions"] == []


def test_un_role_hors_de_la_relecture_est_refuse(application, jeton_de):
    relecture = application("relecture")

    for role in ("caissier", "pharmacien", "agent de numérisation"):
        porteur = _porteur(jeton_de(role))
        assert relecture.get(f"{RELECTURE}/taches", headers=porteur).status_code == 403
        assert relecture.get(f"{RELECTURE}/suivi", headers=porteur).status_code == 403


def test_une_tache_inconnue_n_existe_pas(application, jeton_de):
    relecture = application("relecture")

    assert relecture.get(f"{RELECTURE}/taches/inconnue", headers=_porteur(jeton_de("agent de relecture"))).status_code == 404
    assert relecture.get(f"{RELECTURE}/taches/inconnue", headers=_porteur(jeton_de("médecin"))).status_code == 404
