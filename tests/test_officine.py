"""Acteur officine (F3.7) : une officine vérifie une ordonnance par son numéro, sans voir le patient,
et déclare les lignes qu'elle a vendues ; une ligne payée à la caisse d'un établissement ne s'y vend pas.

Le parcours part de soin (cas, visite et ordonnance) au CNHU : chaque test prescrit sa propre
ordonnance, à un patient réservé aux tests, autre que celui de `tests/test_pharmacie.py`.
"""

from collections.abc import Callable
from typing import Any

import httpx
import pytest

IBUPROFENE = "MED-IBUPROFENE-400"
PARACETAMOL = "MED-PARACETAMOL-500"


def _porteur(jeton: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {jeton}"}


@pytest.fixture(scope="module")
def patient(jeu: Callable[[str], dict[str, Any]]) -> dict[str, Any]:
    """Un patient réservé aux tests, autre que celui de la pharmacie d'établissement."""
    reserves = [p for p in jeu("patients")["patient"] if p.get("reserve_aux_tests") and p.get("npi")]
    return reserves[1]


@pytest.fixture(scope="module")
def prescrire(
    application: Callable[[str], httpx.Client], jeton_de: Callable[[str], str], patient: dict[str, Any]
) -> Callable[[], str]:
    """Le médecin du CNHU ouvre un cas et prescrit ibuprofène et paracétamol : rend le numéro."""
    soin = application("soin")
    medecin = _porteur(jeton_de("médecin"))
    npi = patient["npi"]

    def une_ordonnance() -> str:
        cas = soin.post(f"/api/soin/patients/{npi}/cas", json={"motif": "Douleurs, essai officine"}, headers=medecin)
        assert cas.status_code in (200, 201), cas.text
        visite = soin.post(
            f"/api/soin/cas/{cas.json()['cas_id']}/visites",
            json={
                "type": "consultation",
                "motif": "Douleurs",
                "mesures": [],
                "ordonnance": [
                    {"produit": IBUPROFENE, "quantite": 10, "dose": 1, "moments": ["matin", "soir"], "jours": 5},
                    {"produit": PARACETAMOL, "quantite": 12, "dose": 1, "moments": ["matin", "soir"], "jours": 6},
                ],
            },
            headers=medecin,
        )
        assert visite.status_code in (200, 201), visite.text
        return str(visite.json()["numero_ordonnance"])

    return une_ordonnance


def _par_libelle(ordonnance: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {ligne["libelle"].split()[0]: ligne for ligne in ordonnance["lignes"]}


def test_l_officine_verifie_l_ordonnance_sans_voir_le_patient_et_vend_en_partie(
    application, jeton_de, prescrire, patient
):
    numero = prescrire()
    pharmacie = application("pharmacie")
    officine = _porteur(jeton_de("officine"))

    vue = pharmacie.get(f"/api/pharmacie/officine/ordonnances/{numero}", headers=officine)
    assert vue.status_code == 200, vue.text
    ordonnance = vue.json()
    assert ordonnance["numero"] == numero
    assert ordonnance["prescripteur"] and ordonnance["date"] and ordonnance["etablissement"]
    # La portée minimale : ni nom, ni prénoms, ni NPI du patient.
    assert "patient" not in ordonnance
    for trace in (patient["nom"], *patient["prenoms"], patient["npi"]):
        assert trace not in vue.text
    ibuprofene = _par_libelle(ordonnance)["Ibuprofène"]
    assert ibuprofene["vendable"] and (ibuprofene["prescrite"], ibuprofene["reste"]) == (10, 10)

    chemin = f"/api/pharmacie/officine/ordonnances/{numero}/ventes"
    vente = pharmacie.post(chemin, json={"lignes": [{"id": ibuprofene["id"], "quantite": 4}]}, headers=officine)
    assert vente.status_code == 201, vente.text
    assert vente.json()["delivrances"][0]["reste"] == 6

    apres = _par_libelle(pharmacie.get(f"/api/pharmacie/officine/ordonnances/{numero}", headers=officine).json())
    assert (apres["Ibuprofène"]["remise"], apres["Ibuprofène"]["reste"]) == (4, 6)

    au_dela = pharmacie.post(chemin, json={"lignes": [{"id": ibuprofene["id"], "quantite": 7}]}, headers=officine)
    assert au_dela.status_code == 409

    deux_fois = pharmacie.post(
        chemin,
        json={"lignes": [{"id": ibuprofene["id"], "quantite": 1}, {"id": ibuprofene["id"], "quantite": 1}]},
        headers=officine,
    )
    assert deux_fois.status_code == 422
    assert pharmacie.post(chemin, json={"lignes": []}, headers=officine).status_code == 422


def test_une_ligne_payee_a_la_caisse_ne_se_vend_pas_en_officine(application, jeton_de, prescrire):
    numero = prescrire()
    pharmacie = application("pharmacie")
    officine = _porteur(jeton_de("officine"))
    caisse = application("caisse")
    caissier = _porteur(jeton_de("caissier"))

    # Le caissier n'atteint pas la route de l'officine.
    refus = pharmacie.get(f"/api/pharmacie/officine/ordonnances/{numero}", headers=caissier)
    assert refus.status_code == 403

    avant = _par_libelle(pharmacie.get(f"/api/pharmacie/officine/ordonnances/{numero}", headers=officine).json())
    paracetamol_id = avant["Paracétamol"]["id"]
    assert avant["Paracétamol"]["vendable"]
    encaissement = caisse.post(
        f"/api/caisse/ordonnances/{numero}/encaissements", json={"lignes": [paracetamol_id]}, headers=caissier
    )
    assert encaissement.status_code in (200, 201), encaissement.text

    lignes = _par_libelle(pharmacie.get(f"/api/pharmacie/officine/ordonnances/{numero}", headers=officine).json())
    paracetamol, ibuprofene = lignes["Paracétamol"], lignes["Ibuprofène"]
    assert not paracetamol["vendable"]
    assert "payée à la caisse" in paracetamol["raison"]
    assert ibuprofene["vendable"]

    vente = pharmacie.post(
        f"/api/pharmacie/officine/ordonnances/{numero}/ventes",
        json={"lignes": [{"id": paracetamol["id"], "quantite": 1}]},
        headers=officine,
    )
    assert vente.status_code == 409
