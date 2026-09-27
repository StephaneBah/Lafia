"""La caisse : le caissier tape le numéro d'ordonnance, voit les lignes tarifées par son établissement,
en encaisse, et ne peut pas encaisser deux fois la même ligne.

L'ordonnance vient du service soin : un médecin du CNHU ouvre un cas et y enregistre une visite.
"""

import pytest

from conftest import COOKIE_DE_SESSION, jeton_pose, par_cookie

ETABLISSEMENT = "cnhu-hkm"
# Prix unitaires du CNHU, CHU national (donnees/src/donnees/catalogue.toml).
LIGNES_PRESCRITES = [
    {"produit": "MED-PARACETAMOL-500", "quantite": 6, "prix": 25},
    {"produit": "MED-AMOXICILLINE-500", "quantite": 10, "prix": 60},
]


def _porteur(jeton: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {jeton}"}


def _patient_id(soin, en_tete: dict[str, str], npi: str) -> str:
    """Le NPI n'entre qu'une fois, dans le corps de la recherche : les routes de soin prennent l'identifiant du Patient."""
    trouve = soin.post("/api/soin/recherche", json={"npi": npi}, headers=en_tete)
    assert trouve.status_code == 200, trouve.text
    return str(trouve.json()["patient_id"])


def _compte(comptes, role: str, etablissement: str):
    return next(c for c in comptes if c.role == role and c.etablissement == etablissement and not c.reserve_aux_tests)


@pytest.fixture(scope="module")
def numero_d_ordonnance(application, comptes, connecter, jeu) -> str:
    """Une ordonnance neuve du CNHU, à deux lignes, écrite par un médecin par le service soin."""
    medecin = _compte(comptes, "médecin", ETABLISSEMENT)
    jeton = jeton_pose(connecter(medecin))
    npi = next(p["npi"] for p in jeu("patients")["patient"] if not p.get("reserve_aux_tests"))
    soin = application("soin")

    patient_id = _patient_id(soin, _porteur(jeton), npi)
    cas = soin.post(
        f"/api/soin/patients/{patient_id}/cas", json={"motif": "Fièvre depuis trois jours"}, headers=_porteur(jeton)
    )
    assert cas.status_code in (200, 201), cas.text
    visite = soin.post(
        f"/api/soin/cas/{cas.json()['cas_id']}/visites",
        json={
            "type": "consultation",
            "motif": "Fièvre depuis trois jours",
            "mesures": [],
            "ordonnance": [
                {"produit": l["produit"], "quantite": l["quantite"], "dose": 1, "moments": ["matin"], "jours": 3}
                for l in LIGNES_PRESCRITES
            ],
        },
        headers=_porteur(jeton),
    )
    assert visite.status_code in (200, 201), visite.text
    return visite.json()["numero_ordonnance"]


def test_le_caissier_encaisse_des_lignes_aux_tarifs_de_son_etablissement_et_une_seule_fois(
    application, comptes, connecter, numero_d_ordonnance
):
    caissier = jeton_pose(connecter(_compte(comptes, "caissier", ETABLISSEMENT)))
    caisse = application("caisse")
    # Saisi comme au clavier, sans tirets ni majuscules.
    saisie = numero_d_ordonnance.replace("-", "").lower()

    lue = caisse.get(f"/api/caisse/ordonnances/{saisie}", headers=par_cookie(**{COOKIE_DE_SESSION: caissier}))
    assert lue.status_code == 200, lue.text
    ordonnance = lue.json()
    assert ordonnance["numero"] == numero_d_ordonnance
    assert ordonnance["patient"]["nom"] and ordonnance["prescripteur"]
    montants = sorted(l["montant"] for l in ordonnance["lignes"])
    assert montants == sorted(l["quantite"] * l["prix"] for l in LIGNES_PRESCRITES)
    assert not any(l["payee"] for l in ordonnance["lignes"])
    assert ordonnance["total_a_payer"] == sum(montants)

    premiere = ordonnance["lignes"][0]
    paye = caisse.post(
        f"/api/caisse/ordonnances/{numero_d_ordonnance}/encaissements",
        json={"lignes": [premiere["id"]]},
        headers=_porteur(caissier),
    )
    assert paye.status_code == 201, paye.text
    recepisse = paye.json()
    assert recepisse["recepisse"].startswith("REC-")
    assert recepisse["montant"] == premiere["montant"]
    assert [l["id"] for l in recepisse["lignes"]] == [premiere["id"]]

    apres = caisse.get(f"/api/caisse/ordonnances/{numero_d_ordonnance}", headers=_porteur(caissier)).json()
    assert {l["id"]: l["payee"] for l in apres["lignes"]}[premiere["id"]] is True
    assert apres["total_a_payer"] == sum(montants) - premiere["montant"]

    deux_fois = caisse.post(
        f"/api/caisse/ordonnances/{numero_d_ordonnance}/encaissements",
        json={"lignes": [l["id"] for l in ordonnance["lignes"]]},
        headers=_porteur(caissier),
    )
    assert deux_fois.status_code == 409

    inconnue = caisse.post(
        f"/api/caisse/ordonnances/{numero_d_ordonnance}/encaissements",
        json={"lignes": ["pas-une-ligne"]},
        headers=_porteur(caissier),
    )
    assert inconnue.status_code == 422

    relu = caisse.get(f"/api/caisse/recepisses/{recepisse['recepisse']}", headers=_porteur(caissier))
    assert relu.status_code == 200
    assert relu.json()["montant"] == premiere["montant"]


def test_un_autre_etablissement_ou_un_autre_role_ne_voit_pas_l_ordonnance(
    application, comptes, connecter, numero_d_ordonnance
):
    caisse = application("caisse")
    ailleurs = jeton_pose(connecter(_compte(comptes, "caissier", "chu-mel")))

    assert caisse.get(f"/api/caisse/ordonnances/{numero_d_ordonnance}", headers=_porteur(ailleurs)).status_code == 404
    assert (
        caisse.post(
            f"/api/caisse/ordonnances/{numero_d_ordonnance}/encaissements",
            json={"lignes": ["1"]},
            headers=_porteur(ailleurs),
        ).status_code
        == 404
    )

    medecin = jeton_pose(connecter(_compte(comptes, "médecin", ETABLISSEMENT)))
    assert caisse.get(f"/api/caisse/ordonnances/{numero_d_ordonnance}", headers=_porteur(medecin)).status_code == 403
