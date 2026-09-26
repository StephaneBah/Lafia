"""Jeu de démonstration : ce que le noyau tient après chaque `docker compose up`.

Le jeu est écrit dans `donnees/`, dans le vocabulaire de Lafia ; le conteneur `chargement` le traduit
en FHIR et l'écrit dans le noyau. Ces tests comparent l'un à l'autre : pour chaque chose du jeu, ce que
le noyau en dit. Le noyau ne s'observe pas par la passerelle : ils le lisent de l'intérieur de la pile
(fixture `noyau`), et sont sautés quand elle tourne ailleurs.
"""

import re
from datetime import date
from typing import Any

TYPE_DE_STRUCTURE = "https://lafia.bj/fhir/CodeSystem/type-de-structure"
ROLE = "https://lafia.bj/fhir/CodeSystem/role"
NPI = "https://npi.gouv.bj"
PAYS = "urn:iso:std:iso:3166"
LANGUE = "urn:ietf:bcp:47"
LIEU_DE_NAISSANCE = "http://hl7.org/fhir/StructureDefinition/patient-birthPlace"
NATIONALITE = "http://hl7.org/fhir/StructureDefinition/patient-nationality"
SEXES = {"female": "féminin", "male": "masculin"}
CATALOGUE = "https://lafia.bj/fhir/CodeSystem/catalogue"
ATC = "http://www.whocc.no/atc"
# Identifiant d'un tarif : `<établissement>:<code du produit>`, que la caisse cherche en une fois.
TARIF = "https://lafia.bj/fhir/identifiant/tarif"

# Formats qui garantissent qu'aucune donnée du jeu n'est celle d'une personne réelle.
NPI_SYNTHETIQUE = re.compile(r"000000\d{7}")
TELEPHONE_SYNTHETIQUE = re.compile(r"\+229 01 00 \d\d \d\d \d\d")
# Code carnet : deux groupes de trois caractères, sans 0, O, 1, I ni L.
CODE_CARNET = re.compile(r"[2-9A-HJKMNP-Z]{3}-[2-9A-HJKMNP-Z]{3}")


def _code(concept: dict[str, Any], systeme: str) -> str | None:
    """Le code d'un CodeableConcept dans `systeme`, s'il en porte un."""
    return next((c["code"] for c in concept.get("coding", []) if c["system"] == systeme), None)


def _structure(organization: dict[str, Any]) -> dict[str, Any]:
    """Ce que le noyau dit d'un établissement ou d'une officine, dans les termes du jeu."""
    (adresse,) = organization["address"]
    (type_,) = organization["type"]
    return {
        "nom": organization["name"],
        "type": _code(type_, TYPE_DE_STRUCTURE),
        "departement": adresse["state"],
        "commune": adresse["city"],
    }


def test_etablissements_et_officines_sont_des_organizations_avec_leur_type(jeu, noyau):
    etablissements = jeu("etablissements")["etablissement"]
    officines = jeu("officines")["officine"]
    attendues = {
        e["id"]: {"nom": e["nom"], "type": e["niveau"], "departement": e["departement"], "commune": e["commune"]}
        for e in etablissements
    } | {
        o["id"]: {"nom": o["nom"], "type": "officine", "departement": o["departement"], "commune": o["commune"]}
        for o in officines
    }

    reponses = noyau([f"Organization/{id_}" for id_ in attendues])

    assert [r.statut for r in reponses] == [200] * len(attendues)
    assert {r.ressource["id"]: _structure(r.ressource) for r in reponses} == attendues


def _agent(practitioner: dict[str, Any]) -> dict[str, Any]:
    """Ce que le noyau dit d'un agent, dans les termes du jeu."""
    (nom,) = practitioner["name"]
    (qualification,) = practitioner["qualification"]
    return {"nom": nom["family"], "prenoms": nom["given"], "role": _code(qualification["code"], ROLE)}


def test_chaque_agent_est_un_practitioner_du_noyau(jeu, noyau):
    attendus = {a["id"]: {"nom": a["nom"], "prenoms": a["prenoms"], "role": a["role"]} for a in jeu("agents")["agent"]}

    reponses = noyau([f"Practitioner/{id_}" for id_ in attendus])

    assert [r.statut for r in reponses] == [200] * len(attendus)
    assert {r.ressource["id"]: _agent(r.ressource) for r in reponses} == attendus


def test_chaque_compte_d_agent_designe_un_etablissement_du_noyau(jeu, noyau):
    etablissements = sorted({c["etablissement"] for a in jeu("agents")["agent"] for c in a["compte"]})

    reponses = noyau([f"Organization/{id_}" for id_ in etablissements])

    assert [r.statut for r in reponses] == [200] * len(etablissements)
    # Un établissement, jamais une officine : une officine n'a pas d'agents.
    assert "officine" not in [_structure(r.ressource)["type"] for r in reponses]


def _extension(ressource: dict[str, Any], url: str) -> dict[str, Any]:
    (extension,) = [e for e in ressource.get("extension", []) if e["url"] == url]
    return extension


def _telephone(point_de_contact: dict[str, Any]) -> str:
    (telephone,) = [t["value"] for t in point_de_contact["telecom"] if t["system"] == "phone"]
    return telephone


def _patient(patient: dict[str, Any]) -> dict[str, Any]:
    """Ce que le noyau dit d'un patient, dans les termes du jeu."""
    (npi,) = [i["value"] for i in patient["identifier"] if i["system"] == NPI]
    (nom,) = patient["name"]
    (adresse,) = patient["address"]
    naissance = _extension(patient, LIEU_DE_NAISSANCE)["valueAddress"]
    (nationalite,) = [e for e in _extension(patient, NATIONALITE)["extension"] if e["url"] == "code"]
    lu = {
        "id": patient["id"],
        "npi": npi,
        "nom": nom["family"],
        "prenoms": nom["given"],
        "sexe": SEXES[patient["gender"]],
        "naissance": date.fromisoformat(patient["birthDate"]),
        "lieu_de_naissance": {"commune": naissance["city"], "pays": naissance["country"]},
        "nationalite": _code(nationalite["valueCodeableConcept"], PAYS),
        "adresse": {
            "departement": adresse["state"],
            "commune": adresse["city"],
            "arrondissement": adresse["district"],
            "quartier": " ".join(adresse["line"]),
        },
        "langues": [_code(c["language"], LANGUE) for c in patient["communication"]],
    }
    if "telecom" in patient:
        lu["telephone"] = _telephone(patient)
    if "contact" in patient:
        (contact,) = patient["contact"]
        lu["personne_a_prevenir"] = {
            "nom": contact["name"]["family"],
            "prenoms": contact["name"]["given"],
            "relation": contact["relationship"][0]["text"],
            "telephone": _telephone(contact),
        }
    return lu


def test_chaque_patient_se_trouve_par_son_npi_avec_sa_fiche(jeu, noyau):
    patients = jeu("patients")["patient"]

    reponses = noyau([f"Patient?identifier={NPI}|{p['npi']}" for p in patients])

    trouves = [[e["resource"] for e in r.ressource.get("entry", [])] for r in reponses]
    assert [len(t) for t in trouves] == [1] * len(patients)
    attendus = [{cle: v for cle, v in p.items() if cle != "reserve_aux_tests"} for p in patients]
    assert [_patient(patient) for (patient,) in trouves] == attendus


def _tarif(charge_item_definition: dict[str, Any]) -> dict[str, Any]:
    """Ce que le noyau dit d'un tarif, dans les termes du jeu."""
    (groupe,) = charge_item_definition["propertyGroup"]
    (prix,) = groupe["priceComponent"]
    (lieu,) = charge_item_definition["useContext"]
    return {
        "etablissement": lieu["valueReference"]["reference"],
        "code": _code(charge_item_definition["code"], CATALOGUE),
        "libelle": charge_item_definition["title"],
        "atc": _code(charge_item_definition["code"], ATC),
        "prix": (prix["type"], prix["amount"]["value"], prix["amount"]["currency"]),
    }


def test_chaque_produit_a_un_tarif_dans_chaque_etablissement_trouve_en_une_recherche(jeu, noyau):
    paires = [(e, p) for e in jeu("etablissements")["etablissement"] for p in jeu("catalogue")["produit"]]

    reponses = noyau([f"ChargeItemDefinition?identifier={TARIF}|{e['id']}:{p['code']}" for e, p in paires])

    trouves = [[e["resource"] for e in r.ressource.get("entry", [])] for r in reponses]
    assert [len(t) for t in trouves] == [1] * len(paires)
    assert [_tarif(tarif) for (tarif,) in trouves] == [
        {
            "etablissement": f"Organization/{e['id']}",
            "code": p["code"],
            "libelle": p["libelle"],
            "atc": p.get("atc"),
            "prix": ("base", p["prix"][e["niveau"]], "XOF"),
        }
        for e, p in paires
    ]


def test_aucune_officine_n_a_de_tarif(jeu, noyau):
    officines = {f"Organization/{o['id']}" for o in jeu("officines")["officine"]}

    (reponse,) = noyau(["ChargeItemDefinition?_count=200"])

    lieux = {_tarif(e["resource"])["etablissement"] for e in reponse.ressource.get("entry", [])}
    # Témoin : les tarifs des établissements sont bien lus. Sans eux, l'absence ne prouverait rien.
    assert "Organization/cnhu-hkm" in lieux
    assert lieux & officines == set()


def test_aucun_npi_ni_telephone_du_jeu_ne_peut_etre_celui_d_une_personne_reelle(jeu):
    patients = jeu("patients")["patient"]
    npis = [p["npi"] for p in patients] + [c["npi"] for c in jeu("citoyens")["citoyen"]]
    telephones = [p["telephone"] for p in patients if "telephone" in p] + [
        p["personne_a_prevenir"]["telephone"] for p in patients if "personne_a_prevenir" in p
    ]

    assert [npi for npi in npis if not NPI_SYNTHETIQUE.fullmatch(npi)] == []
    assert [t for t in telephones if not TELEPHONE_SYNTHETIQUE.fullmatch(t)] == []


def test_chaque_citoyen_de_demonstration_est_un_patient_du_noyau_avec_un_code_carnet(jeu, noyau):
    citoyens = jeu("citoyens")["citoyen"]

    reponses = noyau([f"Patient?identifier={NPI}|{c['npi']}" for c in citoyens])

    assert [len(r.ressource.get("entry", [])) for r in reponses] == [1] * len(citoyens)
    assert [c["code_carnet"] for c in citoyens if not CODE_CARNET.fullmatch(c["code_carnet"])] == []


def _versions(jeu, noyau) -> dict[str, str]:
    """La version de chaque ressource du jeu dans le noyau, lue comme les tests ci-dessus la trouvent."""
    etablissements = jeu("etablissements")["etablissement"]
    chemins = [
        *(f"Organization/{e['id']}" for e in etablissements),
        *(f"Organization/{o['id']}" for o in jeu("officines")["officine"]),
        *(f"Practitioner/{a['id']}" for a in jeu("agents")["agent"]),
        *(f"Patient?identifier={NPI}|{p['npi']}" for p in jeu("patients")["patient"]),
        *(
            f"ChargeItemDefinition?identifier={TARIF}|{e['id']}:{p['code']}"
            for e in etablissements
            for p in jeu("catalogue")["produit"]
        ),
    ]
    versions = {}
    for reponse in noyau(chemins):
        recherche = reponse.ressource["resourceType"] == "Bundle"
        for ressource in [e["resource"] for e in reponse.ressource["entry"]] if recherche else [reponse.ressource]:
            versions[f"{ressource['resourceType']}/{ressource['id']}"] = ressource["meta"]["versionId"]
    assert len(versions) == len(chemins)
    return versions


def test_un_second_chargement_ne_change_aucune_version(jeu, noyau, docker):
    avant = _versions(jeu, noyau)

    chargement = docker("compose", "run", "--rm", "--no-deps", "-T", "chargement")

    assert chargement.returncode == 0, chargement.stderr
    assert _versions(jeu, noyau) == avant
