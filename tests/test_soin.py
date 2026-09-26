"""Le service soin : un soignant ouvre un cas, y enregistre une visite et son ordonnance, relit le
dossier ; sans relation de soin, le dossier lui reste fermé, sauf par un accès d'urgence."""

import re

from conftest import jeton_pose

# Un patient du jeu de démonstration, ni citoyen de démonstration ni réservé aux tests.
NPI = "0000001317462"
ORDONNANCE = r"ORD-[2-9A-HJKMNP-Z]{3}-[2-9A-HJKMNP-Z]{3}"


def _porteur(jeton: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {jeton}"}


def test_une_visite_avec_ordonnance_entre_au_dossier_sous_un_numero(application, jeton_de):
    soin = application("soin")
    medecin = _porteur(jeton_de("médecin"))

    catalogue = soin.get("/api/soin/catalogue", headers=medecin).json()
    produit = next(p["code"] for p in catalogue["produits"] if p["code"].startswith("MED-"))

    cas = soin.post(f"/api/soin/patients/{NPI}/cas", json={"motif": "Fièvre"}, headers=medecin)
    assert cas.status_code == 201
    cas_id = cas.json()["cas_id"]

    visite = soin.post(
        f"/api/soin/cas/{cas_id}/visites",
        json={
            "type": "consultation",
            "motif": "Fièvre depuis deux jours",
            "mesures": [{"code": "8310-5", "valeur": 38.6}, {"code": "85354-9", "valeur": 12, "valeur2": 8}],
            "diagnostic": {"code": "paludisme", "confirme": True},
            "ordonnance": [{"produit": produit, "quantite": 6, "dose": 1, "moments": ["matin", "soir"], "jours": 3}],
        },
        headers=medecin,
    )
    assert visite.status_code == 201, visite.text
    numero = visite.json()["numero_ordonnance"]
    assert re.fullmatch(ORDONNANCE, numero)

    fiche = soin.get(f"/api/soin/patients/{NPI}", headers=medecin).json()
    assert fiche["relation_de_soin"] is True
    assert cas_id in {c["id"] for c in fiche["cas"]}

    dossier = soin.get(f"/api/soin/patients/{NPI}/dossier", headers=medecin)
    assert dossier.status_code == 200
    (lu,) = [c for c in dossier.json()["cas"] if c["id"] == cas_id]
    (enregistree,) = lu["visites"]
    assert enregistree["ordonnance"]["numero"] == numero
    assert enregistree["ordonnance"]["lignes"][0]["moments"] == ["matin", "soir"]
    assert enregistree["diagnostics"][0]["confirme"] is True
    assert {m["code"] for m in enregistree["mesures"]} == {"8310-5", "85354-9"}


def test_sans_relation_de_soin_le_dossier_reste_ferme_sauf_acces_d_urgence(
    application, jeton_de, comptes, compte_de, connecter
):
    soin = application("soin")
    ici = compte_de("médecin")
    cas = soin.post(f"/api/soin/patients/{NPI}/cas", json={"motif": "Toux"}, headers=_porteur(jeton_de("médecin")))
    assert cas.status_code == 201

    # Un médecin d'un autre établissement, qui n'a jamais vu ce patient : ni lire, ni clore.
    ailleurs = next(
        c for c in comptes
        if c.role == "médecin" and not c.reserve_aux_tests and c.etablissement not in (ici.etablissement, "chu-mel")
    )
    autre = _porteur(jeton_pose(connecter(ailleurs)))
    # Un passage interrompu a pu laisser ouvert un cas d'urgence là-bas : le clore rend la suite rejouable.
    for reste in soin.get(f"/api/soin/patients/{NPI}", headers=autre).json()["cas"]:
        if reste.get("de_mon_etablissement"):
            soin.post(f"/api/soin/cas/{reste['id']}/cloture", headers=autre)
    assert soin.get(f"/api/soin/patients/{NPI}", headers=autre).json()["relation_de_soin"] is False
    assert soin.get(f"/api/soin/patients/{NPI}/dossier", headers=autre).status_code == 403
    assert soin.post(f"/api/soin/cas/{cas.json()['cas_id']}/cloture", headers=autre).status_code == 403

    # Un infirmier ne clôt pas un cas, même de son établissement ; un caissier n'entre pas au service soin.
    assert soin.post(f"/api/soin/cas/{cas.json()['cas_id']}/cloture", headers=_porteur(jeton_de("infirmier"))).status_code == 403
    assert soin.get(f"/api/soin/patients/{NPI}", headers=_porteur(jeton_de("caissier"))).status_code == 403

    # L'accès d'urgence exige une raison, puis ouvre le dossier.
    assert soin.post(f"/api/soin/patients/{NPI}/acces-urgence", json={"raison": "vite"}, headers=autre).status_code == 422
    urgence = soin.post(
        f"/api/soin/patients/{NPI}/acces-urgence", json={"raison": "Patient inconscient à l'arrivée"}, headers=autre
    )
    assert urgence.status_code == 201
    assert soin.get(f"/api/soin/patients/{NPI}/dossier", headers=autre).status_code == 200

    # Le cas d'urgence clos, le dossier se referme : la suite se rejoue sur la même pile.
    assert soin.post(f"/api/soin/cas/{urgence.json()['cas_id']}/cloture", headers=autre).status_code == 200
    assert soin.get(f"/api/soin/patients/{NPI}/dossier", headers=autre).status_code == 403
