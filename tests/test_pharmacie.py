"""Acteur pharmacie (F3.5) : le comptoir d'un établissement remet les lignes payées à sa caisse,
s'arrête devant une allergie qui concerne une ligne, et remet en partie si besoin.

Le parcours part de soin (allergie, cas, visite et ordonnance) et passe par la caisse du même
établissement : chaque test prescrit sa propre ordonnance, à un patient réservé aux tests.
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
def npi(jeu: Callable[[str], dict[str, Any]]) -> str:
    """Un patient réservé aux tests : ses allergies et ordonnances d'essai ne touchent pas la démonstration."""
    reserves = [p for p in jeu("patients")["patient"] if p.get("reserve_aux_tests") and p.get("npi")]
    return reserves[0]["npi"]


@pytest.fixture(scope="module")
def prescrire(application: Callable[[str], httpx.Client], jeton_de: Callable[[str], str], npi: str) -> Callable[[], str]:
    """Le médecin du CNHU déclare une allergie aux AINS, ouvre un cas et prescrit ibuprofène et
    paracétamol : rend le numéro d'ordonnance."""
    soin = application("soin")
    medecin = _porteur(jeton_de("médecin"))

    def une_ordonnance() -> str:
        cas = soin.post(f"/api/soin/patients/{npi}/cas", json={"motif": "Douleurs, essai pharmacie"}, headers=medecin)
        assert cas.status_code in (200, 201), cas.text
        allergie = soin.post(
            f"/api/soin/patients/{npi}/allergies",
            json={"code_atc": "M01A", "libelle": "AINS"},
            headers=medecin,
        )
        assert allergie.status_code in (200, 201), allergie.text
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


def _payer(application: Callable[[str], httpx.Client], jeton_de: Callable[[str], str], numero: str) -> None:
    caisse = application("caisse")
    caissier = _porteur(jeton_de("caissier"))
    ordonnance = caisse.get(f"/api/caisse/ordonnances/{numero}", headers=caissier)
    assert ordonnance.status_code == 200, ordonnance.text
    lignes = [ligne["id"] for ligne in ordonnance.json()["lignes"]]
    encaissement = caisse.post(f"/api/caisse/ordonnances/{numero}/encaissements", json={"lignes": lignes}, headers=caissier)
    assert encaissement.status_code in (200, 201), encaissement.text


def test_le_pharmacien_remet_en_partie_apres_avoir_reconnu_l_allergie(application, jeton_de, prescrire):
    numero = prescrire()
    _payer(application, jeton_de, numero)
    pharmacie = application("pharmacie")
    pharmacien = _porteur(jeton_de("pharmacien"))

    vue = pharmacie.get(f"/api/pharmacie/ordonnances/{numero}", headers=pharmacien)
    assert vue.status_code == 200, vue.text
    ordonnance = vue.json()
    assert ordonnance["numero"] == numero
    lignes = {ligne["libelle"].split()[0]: ligne for ligne in ordonnance["lignes"]}
    ibuprofene, paracetamol = lignes["Ibuprofène"], lignes["Paracétamol"]
    assert ibuprofene["payee"] and paracetamol["payee"]
    assert (ibuprofene["prescrite"], ibuprofene["remise"], ibuprofene["reste"]) == (10, 0, 10)
    assert ibuprofene["posologie"]["moments"] == ["matin", "soir"]
    # L'allergie aux AINS concerne l'ibuprofène, pas le paracétamol.
    concernees = {id_ for allergie in ordonnance["allergies"] for id_ in allergie["lignes"]}
    assert ibuprofene["id"] in concernees
    assert paracetamol["id"] not in concernees

    chemin = f"/api/pharmacie/ordonnances/{numero}/delivrances"
    sans_reconnaitre = pharmacie.post(chemin, json={"lignes": [{"id": ibuprofene["id"], "quantite": 4}]}, headers=pharmacien)
    assert sans_reconnaitre.status_code == 409

    remise = pharmacie.post(
        chemin,
        json={"lignes": [{"id": ibuprofene["id"], "quantite": 4}], "allergie_reconnue": True},
        headers=pharmacien,
    )
    assert remise.status_code == 201, remise.text
    assert remise.json()["delivrances"][0]["reste"] == 6

    apres = pharmacie.get(f"/api/pharmacie/ordonnances/{numero}", headers=pharmacien).json()
    ibuprofene_apres = next(l for l in apres["lignes"] if l["id"] == ibuprofene["id"])
    assert (ibuprofene_apres["remise"], ibuprofene_apres["reste"], ibuprofene_apres["statut"]) == (4, 6, "partiel")

    au_dela = pharmacie.post(
        chemin,
        json={"lignes": [{"id": ibuprofene["id"], "quantite": 7}], "allergie_reconnue": True},
        headers=pharmacien,
    )
    assert au_dela.status_code == 409


def test_une_ligne_non_payee_ne_se_remet_pas_et_le_caissier_n_a_pas_acces(application, jeton_de, prescrire):
    numero = prescrire()
    pharmacie = application("pharmacie")
    pharmacien = _porteur(jeton_de("pharmacien"))

    vue = pharmacie.get(f"/api/pharmacie/ordonnances/{numero}", headers=pharmacien)
    assert vue.status_code == 200, vue.text
    paracetamol = next(l for l in vue.json()["lignes"] if l["libelle"].startswith("Paracétamol"))
    assert not paracetamol["payee"] and paracetamol["statut"] == "apayer"

    refus = pharmacie.post(
        f"/api/pharmacie/ordonnances/{numero}/delivrances",
        json={"lignes": [{"id": paracetamol["id"], "quantite": 1}]},
        headers=pharmacien,
    )
    assert refus.status_code == 409

    caissier = pharmacie.get(f"/api/pharmacie/ordonnances/{numero}", headers=_porteur(jeton_de("caissier")))
    assert caissier.status_code == 403
