"""Le service relecture (F6, ADR 0009) : un Document ajouté pendant une visite entre au pool ; un agent de
relecture d'un autre département le reçoit dans sa semaine, le trie sans voir qui est le patient ;
utilisable, il est lu par l'Extraction de démonstration ; un médecin prend la Tâche, accepte une
proposition, rejette les autres, et l'antécédent accepté entre au dossier avec l'origine `extraction`.

Le pool sert les plus vieux papiers d'abord : le Document de ce test est daté de 1900, qu'aucun autre
test n'emploie, pour passer devant ceux que la suite dépose ailleurs. L'agent trie chaque papier de 1900
de sa semaine : tous viennent de ce test, au dossier du même patient, et cela libère sa place pour le
passage suivant (une Tâche passée en validation n'est plus à lui).
"""

import base64
import json

from test_soin import page_png

# Un patient du jeu de démonstration, celui des tests de soin.
NPI = "0000001317462"
ANNEE_DU_PAPIER = "1900"


def _porteur(jeton: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {jeton}"}


def test_un_document_est_trie_sans_identite_lu_puis_valide_au_dossier(application, jeton_de, compte_de, jeu):
    soin = application("soin")
    relecture = application("relecture")
    medecin = _porteur(jeton_de("médecin"))
    agent = _porteur(jeton_de("agent de relecture"))
    # L'agent de relecture de démonstration travaille à Parakou ; le médecin, à Cotonou.
    departements = {e["id"]: e["departement"] for e in jeu("etablissements")["etablissement"]}
    assert departements[compte_de("agent de relecture").etablissement] != departements[compte_de("médecin").etablissement]

    trouve = soin.post("/api/soin/recherche", json={"npi": NPI}, headers=medecin)
    assert trouve.status_code == 200, trouve.text
    patient_id = trouve.json()["patient_id"]
    cas = soin.post(f"/api/soin/patients/{patient_id}/cas", json={"motif": "Anciens papiers à relire"}, headers=medecin)
    assert cas.status_code == 201, cas.text
    nom = soin.get(f"/api/soin/patients/{patient_id}", headers=medecin).json()["patient"]["nom"]
    ajoute = soin.post(
        f"/api/soin/patients/{patient_id}/documents",
        data={"type": "carnet", "annee": ANNEE_DU_PAPIER, "lisibilite": "lisible"},
        files=[("pages", ("page-1.png", page_png(), "image/png"))],
        headers=medecin,
    )
    assert ajoute.status_code == 201, ajoute.text

    # La semaine de l'agent : le papier de 1900 y est, à trier, sans rien qui dise de qui il est.
    semaine = relecture.get("/api/relecture/taches", headers=agent)
    assert semaine.status_code == 200, semaine.text
    a_trier = [
        t for t in semaine.json()
        if t["etape"] == "triage" and t["statut"] == "a-faire" and t["document"]["annee"] == ANNEE_DU_PAPIER
    ]
    assert a_trier, semaine.json()
    for tache in a_trier:
        vue = relecture.get(f"/api/relecture/taches/{tache['id']}", headers=agent)
        assert vue.status_code == 200, vue.text
        assert vue.json()["document"]["type"] == "carnet"
        assert vue.json()["document"]["pages"] == 1
        for revelateur in (NPI, nom, patient_id):
            assert revelateur not in vue.text
        page = relecture.get(f"/api/relecture/taches/{tache['id']}/pages/1", headers=agent)
        assert page.status_code == 200
        assert page.content == page_png()

        # Ni le triage par un soignant, ni la validation par l'agent de relecture.
        assert relecture.post(f"/api/relecture/taches/{tache['id']}/triage", json={"verdict": "utilisable"}, headers=medecin).status_code == 403
        assert relecture.post(f"/api/relecture/taches/{tache['id']}/validation", json={"propositions": []}, headers=agent).status_code == 403

        trie = relecture.post(f"/api/relecture/taches/{tache['id']}/triage", json={"verdict": "utilisable"}, headers=agent)
        assert trie.status_code == 200, trie.text
        assert (trie.json()["etape"], trie.json()["verdict"]) == ("validation", "utilisable")
        # Passée en validation, elle n'est plus à lui.
        assert relecture.get(f"/api/relecture/taches/{tache['id']}", headers=agent).status_code == 403

    # Le médecin prend la Tâche en l'ouvrant : les propositions de l'Extraction de démonstration, le texte lu.
    tache_id = a_trier[-1]["id"]
    vue = relecture.get(f"/api/relecture/taches/{tache_id}", headers=medecin)
    assert vue.status_code == 200, vue.text
    lue = vue.json()
    assert (lue["etape"], lue["statut"]) == ("validation", "en-cours")
    assert lue["modele"] == {"nom": "demonstration", "version": "0", "demonstration": True}
    assert "démonstration" in lue["texte"]
    for revelateur in (NPI, nom, patient_id):
        assert revelateur not in vue.text
    types = {p["type"]: p for p in lue["propositions"]}
    assert set(types) == {"Condition", "AllergyIntolerance", "Observation"}
    assert all(0 <= p["confiance"] <= 1 for p in lue["propositions"])
    assert tache_id in [t["id"] for t in relecture.get("/api/relecture/taches", headers=medecin).json()]
    assert relecture.get(f"/api/relecture/taches/{tache_id}/pages/1", headers=medecin).status_code == 200

    # Une proposition inconnue est refusée ; puis l'antécédent accepté, l'allergie rejetée, la mesure tue.
    inconnue = relecture.post(
        f"/api/relecture/taches/{tache_id}/validation", json={"propositions": [{"id": "p99", "decision": "accepter"}]}, headers=medecin
    )
    assert inconnue.status_code == 422
    validee = relecture.post(
        f"/api/relecture/taches/{tache_id}/validation",
        json={
            "propositions": [
                {"id": types["Condition"]["id"], "decision": "accepter"},
                {"id": types["AllergyIntolerance"]["id"], "decision": "rejeter"},
            ]
        },
        headers=medecin,
    )
    assert validee.status_code == 200, validee.text
    ((entree),) = validee.json()["entrees"]
    assert entree["type"] == "Condition"
    assert validee.json()["rejetees"] == 2
    # Validée, la Tâche est close.
    assert relecture.post(f"/api/relecture/taches/{tache_id}/validation", json={"propositions": []}, headers=medecin).status_code == 409

    # L'antécédent est au dossier, dans le bandeau de soin, avec son origine.
    bandeau = soin.get(f"/api/soin/patients/{patient_id}", headers=medecin).json()
    (antecedent,) = [a for a in bandeau["antecedents"] if a["id"] == entree["id"]]
    assert (antecedent["libelle"], antecedent["origine"]) == ("Paludisme", "extraction")
    # L'allergie rejetée n'y est pas entrée.
    assert "Pénicilline" not in [a["libelle"] for a in bandeau["allergies"] if a["origine"] == "extraction"]

    # Les autres Tâches de 1900 prises ici : validées sans rien retenir, pour ne rien laisser en suspens.
    for tache in a_trier[:-1]:
        assert relecture.get(f"/api/relecture/taches/{tache['id']}", headers=medecin).status_code == 200
        assert relecture.post(f"/api/relecture/taches/{tache['id']}/validation", json={"propositions": []}, headers=medecin).status_code == 200

    soin.post(f"/api/soin/cas/{cas.json()['cas_id']}/cloture", headers=medecin)


# Joint extraction depuis relecture, seul conteneur qui le peut, et lit chaque réponse au contrat de
# `commun.extraction` : la page, en base64, arrive sur l'entrée standard.
APPEL_D_EXTRACTION = """
import json, os, sys, httpx
from commun.extraction import DemandeDExtraction, Extraction
page = sys.stdin.read()
reponses = {}
for type_ in sys.argv[1:]:
    demande = DemandeDExtraction(document_id="contrat", type_de_document=type_, pages=[{"format": "image/png", "octets": page}])
    reponse = httpx.post(os.environ["EXTRACTION_URL"] + "/extraire", json=demande.model_dump(), timeout=30)
    reponse.raise_for_status()
    reponses[type_] = Extraction.model_validate(reponse.json()).model_dump()
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
    for type_, extraction in reponses.items():
        assert extraction["modele"] == {"nom": "demonstration", "version": "0"}, type_
        assert "démonstration" in extraction["texte"]
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
    assert [p["ressource"]["resourceType"] for p in reponses["carnet"]["propositions"]] == [
        "Condition",
        "AllergyIntolerance",
        "Observation",
    ]
    (hemoglobine,) = reponses["resultat-analyse"]["propositions"]
    assert hemoglobine["ressource"]["code"]["coding"][0]["code"] == "718-7"
    assert reponses["imagerie"]["propositions"] == []


def test_un_role_hors_de_la_relecture_est_refuse(application, jeton_de):
    relecture = application("relecture")

    for role in ("caissier", "pharmacien", "agent de numérisation"):
        assert relecture.get("/api/relecture/taches", headers=_porteur(jeton_de(role))).status_code == 403


def test_une_tache_inconnue_n_existe_pas(application, jeton_de):
    relecture = application("relecture")

    assert relecture.get("/api/relecture/taches/inconnue", headers=_porteur(jeton_de("agent de relecture"))).status_code == 404
    assert relecture.get("/api/relecture/taches/inconnue", headers=_porteur(jeton_de("médecin"))).status_code == 404
