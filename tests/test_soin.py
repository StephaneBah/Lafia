"""Le service soin : un soignant trouve un patient par son NPI, ouvre un cas, y enregistre une visite
et son ordonnance, note antécédents, traitements au long cours et groupe sanguin, relit le dossier ;
sans relation de soin, le dossier lui reste fermé, sauf par un accès d'urgence."""

import re
import struct
import zlib
from datetime import date

from conftest import jeton_pose

# Un patient du jeu de démonstration, ni citoyen de démonstration ni réservé aux tests.
NPI = "0000001317462"
ORDONNANCE = r"ORD-[2-9A-HJKMNP-Z]{3}-[2-9A-HJKMNP-Z]{3}"


def _porteur(jeton: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {jeton}"}


def _patient_id(soin, en_tete: dict[str, str], npi: str = NPI) -> str:
    """Le NPI n'entre qu'une fois, dans le corps de la recherche : les routes de soin prennent l'identifiant du Patient."""
    trouve = soin.post("/api/soin/recherche", json={"npi": npi}, headers=en_tete)
    assert trouve.status_code == 200, trouve.text
    return str(trouve.json()["patient_id"])


def test_une_visite_avec_ordonnance_entre_au_dossier_sous_un_numero(application, jeton_de):
    soin = application("soin")
    medecin = _porteur(jeton_de("médecin"))

    catalogue = soin.get("/api/soin/catalogue", headers=medecin).json()
    (produit,) = [p for p in catalogue["produits"] if p["code"] == "MED-PARACETAMOL-500"]
    assert produit["forme"] == "comprimé"
    assert soin.post("/api/soin/recherche", json={"npi": "9999999999999"}, headers=medecin).status_code == 404
    patient_id = _patient_id(soin, medecin)

    cas = soin.post(f"/api/soin/patients/{patient_id}/cas", json={"motif": "Fièvre"}, headers=medecin)
    assert cas.status_code == 201
    cas_id = cas.json()["cas_id"]

    visite = soin.post(
        f"/api/soin/cas/{cas_id}/visites",
        json={
            "type": "consultation",
            "motif": "Fièvre depuis deux jours",
            "mesures": [{"code": "8310-5", "valeur": 38.6}, {"code": "85354-9", "valeur": 12, "valeur2": 8}],
            "diagnostic": {"code": "paludisme", "confirme": True},
            "ordonnance": [
                {"produit": produit["code"], "quantite": 6, "dose": 1, "moments": ["matin", "soir"], "jours": 3}
            ],
        },
        headers=medecin,
    )
    assert visite.status_code == 201, visite.text
    numero = visite.json()["numero_ordonnance"]
    assert re.fullmatch(ORDONNANCE, numero)

    bandeau = soin.get(f"/api/soin/patients/{patient_id}", headers=medecin).json()
    assert bandeau["relation_de_soin"] is True
    assert bandeau["patient"]["npi"] == NPI
    assert cas_id in {c["id"] for c in bandeau["cas"]}

    dossier = soin.get(f"/api/soin/patients/{patient_id}/dossier", headers=medecin)
    assert dossier.status_code == 200
    (lu,) = [c for c in dossier.json()["cas"] if c["id"] == cas_id]
    (enregistree,) = lu["visites"]
    assert enregistree["ordonnance"]["numero"] == numero
    (ligne,) = enregistree["ordonnance"]["lignes"]
    assert ligne["moments"] == ["matin", "soir"]
    assert ligne["unite"] == "comprimé"
    assert enregistree["diagnostics"][0]["confirme"] is True
    assert {m["code"] for m in enregistree["mesures"]} == {"8310-5", "85354-9"}
    assert dossier.json()["mesures_series"]["8310-5"][-1]["valeur"] == 38.6


def test_antecedents_traitements_et_groupe_sanguin_restent_au_bandeau(application, jeton_de):
    soin = application("soin")
    medecin = _porteur(jeton_de("médecin"))
    patient_id = _patient_id(soin, medecin)
    cas = soin.post(f"/api/soin/patients/{patient_id}/cas", json={"motif": "Bilan"}, headers=medecin)
    assert cas.status_code == 201

    antecedent = soin.post(
        f"/api/soin/patients/{patient_id}/antecedents",
        json={"type": "chirurgical", "libelle": "Appendicectomie", "depuis": "2015"},
        headers=medecin,
    )
    assert antecedent.status_code == 201, antecedent.text
    familial = soin.post(
        f"/api/soin/patients/{patient_id}/antecedents",
        json={"type": "familial", "libelle": "Diabète de type 2", "lien": "mere"},
        headers=medecin,
    )
    assert familial.status_code == 201, familial.text
    # Un antécédent familial dit le lien de parenté.
    sans_lien = soin.post(
        f"/api/soin/patients/{patient_id}/antecedents", json={"type": "familial", "libelle": "HTA"}, headers=medecin
    )
    assert sans_lien.status_code == 422

    traitement = soin.post(
        f"/api/soin/patients/{patient_id}/traitements",
        json={"produit": "MED-PARACETAMOL-500", "posologie": "1 comprimé le soir", "moments": ["soir"]},
        headers=medecin,
    )
    assert traitement.status_code == 201, traitement.text
    groupe = soin.put(f"/api/soin/patients/{patient_id}/groupe-sanguin", json={"valeur": "o+"}, headers=medecin)
    assert groupe.status_code == 200, groupe.text
    inconnu = soin.put(f"/api/soin/patients/{patient_id}/groupe-sanguin", json={"valeur": "C+"}, headers=medecin)
    assert inconnu.status_code == 422

    # Une allergie se déclare par une classe du catalogue des allergies, et aucune autre.
    catalogue = soin.get("/api/soin/catalogue", headers=medecin).json()
    assert {"code_atc": "J01C", "libelle": "Pénicillines"} in catalogue["allergies"]
    hors_catalogue = soin.post(
        f"/api/soin/patients/{patient_id}/allergies", json={"code_atc": "A10BA"}, headers=medecin
    )
    assert hors_catalogue.status_code == 422

    bandeau = soin.get(f"/api/soin/patients/{patient_id}", headers=medecin).json()
    assert bandeau["groupe_sanguin"] == "O+"
    (note,) = [a for a in bandeau["antecedents"] if a["id"] == antecedent.json()["id"]]
    # Saisi par le soignant, sans Document : une déclaration (ADR 0007).
    assert note == {
        "id": antecedent.json()["id"],
        "type": "chirurgical",
        "libelle": "Appendicectomie",
        "depuis": "2015",
        "actif": True,
        "origine": "declaration",
    }
    assert {
        "id": familial.json()["id"], "lien": "mere", "libelle": "Diabète de type 2", "origine": "declaration"
    } in bandeau["familiaux"]
    (suivi,) = [t for t in bandeau["traitements"] if t["id"] == traitement.json()["id"]]
    assert suivi["moments"] == ["soir"]
    assert suivi["libelle"]

    # Arrêté, le traitement quitte le bandeau.
    arret = soin.post(f"/api/soin/traitements/{traitement.json()['id']}/arret", headers=medecin)
    assert arret.status_code == 200, arret.text
    bandeau = soin.get(f"/api/soin/patients/{patient_id}", headers=medecin).json()
    assert traitement.json()["id"] not in {t["id"] for t in bandeau["traitements"]}
    soin.post(f"/api/soin/cas/{cas.json()['cas_id']}/cloture", headers=medecin)


def test_le_diagnostic_d_un_infirmier_reste_provisoire(application, jeton_de):
    soin = application("soin")
    medecin = _porteur(jeton_de("médecin"))
    infirmier = _porteur(jeton_de("infirmier"))
    patient_id = _patient_id(soin, infirmier)
    cas = soin.post(f"/api/soin/patients/{patient_id}/cas", json={"motif": "Fièvre"}, headers=infirmier)
    assert cas.status_code == 201, cas.text
    cas_id = cas.json()["cas_id"]
    visite = soin.post(
        f"/api/soin/cas/{cas_id}/visites",
        json={"type": "soins-infirmiers", "motif": "Fièvre", "diagnostic": {"code": "paludisme", "confirme": True}},
        headers=infirmier,
    )
    assert visite.status_code == 201, visite.text
    # Hors de la courte liste, un diagnostic est refusé.
    hors_liste = soin.post(
        f"/api/soin/cas/{cas_id}/visites",
        json={"type": "soins-infirmiers", "motif": "Fièvre", "diagnostic": {"code": "grippe-aviaire"}},
        headers=infirmier,
    )
    assert hors_liste.status_code == 422

    dossier = soin.get(f"/api/soin/patients/{patient_id}/dossier", headers=medecin).json()
    (lu,) = [c for c in dossier["cas"] if c["id"] == cas_id]
    (vue,) = lu["visites"]
    assert vue["diagnostics"][0]["confirme"] is False
    soin.post(f"/api/soin/cas/{cas_id}/cloture", headers=medecin)


def test_sans_relation_de_soin_le_dossier_reste_ferme_sauf_acces_d_urgence(
    application, jeton_de, comptes, compte_de, connecter
):
    soin = application("soin")
    ici = compte_de("médecin")
    medecin = _porteur(jeton_de("médecin"))
    patient_id = _patient_id(soin, medecin)
    cas = soin.post(f"/api/soin/patients/{patient_id}/cas", json={"motif": "Toux"}, headers=medecin)
    assert cas.status_code == 201
    cas_id = cas.json()["cas_id"]
    asthme = soin.post(
        f"/api/soin/patients/{patient_id}/antecedents", json={"type": "medical", "libelle": "Asthme"}, headers=medecin
    )
    assert asthme.status_code == 201

    # Un médecin d'un autre établissement, qui n'a jamais vu ce patient : ni lire, ni clore.
    ailleurs = next(
        c for c in comptes
        if c.role == "médecin" and not c.reserve_aux_tests and c.etablissement not in (ici.etablissement, "chu-mel")
    )
    autre = _porteur(jeton_pose(connecter(ailleurs)))
    assert _patient_id(soin, autre) == patient_id
    # Un passage interrompu a pu laisser ouvert un cas d'urgence là-bas : le clore rend la suite rejouable.
    for reste in soin.get(f"/api/soin/patients/{patient_id}", headers=autre).json()["cas"]:
        if reste.get("de_mon_etablissement"):
            soin.post(f"/api/soin/cas/{reste['id']}/cloture", headers=autre)

    # Sans relation de soin : l'identité, les allergies et le groupe sanguin, qui sauvent des vies ;
    # ni antécédents, ni traitements, ni motif des cas d'ailleurs.
    bandeau = soin.get(f"/api/soin/patients/{patient_id}", headers=autre).json()
    assert bandeau["relation_de_soin"] is False
    assert bandeau["patient"]["id"] == patient_id and bandeau["patient"]["nom"]
    assert "allergies" in bandeau and "groupe_sanguin" in bandeau
    assert bandeau["antecedents"] == [] and bandeau["familiaux"] == [] and bandeau["traitements"] == []
    (d_ici,) = [c for c in bandeau["cas"] if c["id"] == cas_id]
    assert d_ici["motif"] is None
    assert soin.get(f"/api/soin/patients/{patient_id}/dossier", headers=autre).status_code == 403
    assert soin.post(f"/api/soin/cas/{cas_id}/cloture", headers=autre).status_code == 403

    # Un infirmier ne clôt pas un cas, même de son établissement ; un caissier n'entre pas au service soin.
    assert soin.post(f"/api/soin/cas/{cas_id}/cloture", headers=_porteur(jeton_de("infirmier"))).status_code == 403
    assert soin.get(f"/api/soin/patients/{patient_id}", headers=_porteur(jeton_de("caissier"))).status_code == 403

    # L'accès d'urgence exige une raison, puis ouvre le dossier.
    trop_court = soin.post(f"/api/soin/patients/{patient_id}/acces-urgence", json={"raison": "vite"}, headers=autre)
    assert trop_court.status_code == 422
    urgence = soin.post(
        f"/api/soin/patients/{patient_id}/acces-urgence",
        json={"raison": "Patient inconscient à l'arrivée"},
        headers=autre,
    )
    assert urgence.status_code == 201
    assert soin.get(f"/api/soin/patients/{patient_id}/dossier", headers=autre).status_code == 200
    # La relation tient par le cas d'urgence, pas par celui d'ailleurs : le clore reste interdit.
    assert soin.post(f"/api/soin/cas/{cas_id}/cloture", headers=autre).status_code == 403

    # Le cas d'urgence clos, le dossier se referme : la suite se rejoue sur la même pile.
    assert soin.post(f"/api/soin/cas/{urgence.json()['cas_id']}/cloture", headers=autre).status_code == 200
    assert soin.get(f"/api/soin/patients/{patient_id}/dossier", headers=autre).status_code == 403
    assert soin.post(f"/api/soin/cas/{cas_id}/cloture", headers=medecin).status_code == 200


def page_png() -> bytes:
    """Une page de test : une image PNG d'un pixel blanc, générée ici plutôt que lue d'un fichier."""

    def morceau(genre: bytes, donnees: bytes) -> bytes:
        return struct.pack(">I", len(donnees)) + genre + donnees + struct.pack(">I", zlib.crc32(genre + donnees))

    entete = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + morceau(b"IHDR", entete)
        + morceau(b"IDAT", zlib.compress(b"\x00\xff\xff\xff"))
        + morceau(b"IEND", b"")
    )


def test_un_document_apporte_par_le_patient_entre_au_dossier_et_une_entree_s_en_reporte(
    application, jeton_de, comptes, compte_de, connecter
):
    soin = application("soin")
    ici = compte_de("médecin")
    medecin = _porteur(jeton_de("médecin"))
    patient_id = _patient_id(soin, medecin)
    cas = soin.post(f"/api/soin/patients/{patient_id}/cas", json={"motif": "Bilan, anciens papiers"}, headers=medecin)
    assert cas.status_code == 201
    page = page_png()

    ajoute = soin.post(
        f"/api/soin/patients/{patient_id}/documents",
        data={"type": "compte-rendu", "annee": "2019", "etablissement": "CHU de Parakou", "lisibilite": "lisible"},
        files=[("pages", ("page-1.png", page, "image/png"))],
        headers=medecin,
    )
    assert ajoute.status_code == 201, ajoute.text
    document_id = ajoute.json()["document_id"]
    assert ajoute.json()["pages"] == 1
    # Un format hors de l'ADR 0008 est refusé, et rien n'en est écrit.
    gif = soin.post(
        f"/api/soin/patients/{patient_id}/documents",
        data={"type": "carnet", "annee": "2019", "lisibilite": "lisible"},
        files=[("pages", ("page.gif", b"GIF89a", "image/gif"))],
        headers=medecin,
    )
    assert gif.status_code == 422
    # Le format se lit aux premiers octets, jamais à ce que la page déclare ; et l'année est passée.
    faux_jpeg = soin.post(
        f"/api/soin/patients/{patient_id}/documents",
        data={"type": "carnet", "annee": "2019", "lisibilite": "lisible"},
        files=[("pages", ("page.jpg", page, "image/jpeg"))],
        headers=medecin,
    )
    assert faux_jpeg.status_code == 422
    a_venir = soin.post(
        f"/api/soin/patients/{patient_id}/documents",
        data={"type": "carnet", "annee": str(date.today().year + 1), "lisibilite": "lisible"},
        files=[("pages", ("page.png", page, "image/png"))],
        headers=medecin,
    )
    assert a_venir.status_code == 422

    liste = soin.get(f"/api/soin/patients/{patient_id}/documents", headers=medecin)
    assert liste.status_code == 200, liste.text
    (document,) = [d for d in liste.json() if d["id"] == document_id]
    assert document["origine"] == "numerisation"
    assert (document["type"], document["libelle"], document["annee"], document["pages"]) == (
        "compte-rendu", "Compte rendu", "2019", 1
    )
    assert document["etablissement"] == "CHU de Parakou"

    lue = soin.get(f"/api/soin/documents/{document_id}/pages/1", headers=medecin)
    assert lue.status_code == 200
    assert lue.headers["content-type"].startswith("image/png")
    assert lue.headers["x-content-type-options"] == "nosniff"
    assert lue.content == page
    assert soin.get(f"/api/soin/documents/{document_id}/pages/2", headers=medecin).status_code == 404

    # Reporté depuis le Document : l'antécédent porte l'origine `report`.
    reporte = soin.post(
        f"/api/soin/patients/{patient_id}/antecedents",
        json={"type": "medical", "libelle": "Drépanocytose", "depuis": "2019", "document_id": document_id},
        headers=medecin,
    )
    assert reporte.status_code == 201, reporte.text
    bandeau = soin.get(f"/api/soin/patients/{patient_id}", headers=medecin).json()
    (antecedent,) = [a for a in bandeau["antecedents"] if a["id"] == reporte.json()["id"]]
    assert antecedent["origine"] == "report"
    # Le Document d'un patient ne fonde aucun report au dossier d'un autre.
    autre_patient = _patient_id(soin, medecin, "0000001204815")
    cas_de_l_autre = soin.post(f"/api/soin/patients/{autre_patient}/cas", json={"motif": "Contrôle"}, headers=medecin)
    assert cas_de_l_autre.status_code == 201
    croise = soin.post(
        f"/api/soin/patients/{autre_patient}/allergies", json={"code_atc": "J01C", "document_id": document_id}, headers=medecin
    )
    assert croise.status_code == 422
    soin.post(f"/api/soin/cas/{cas_de_l_autre.json()['cas_id']}/cloture", headers=medecin)

    # Un médecin d'un autre établissement, sans relation de soin : ni la liste, ni les pages.
    ailleurs = next(
        c for c in comptes
        if c.role == "médecin" and not c.reserve_aux_tests and c.etablissement not in (ici.etablissement, "chu-mel")
    )
    autre = _porteur(jeton_pose(connecter(ailleurs)))
    for reste in soin.get(f"/api/soin/patients/{patient_id}", headers=autre).json()["cas"]:
        if reste.get("de_mon_etablissement"):
            soin.post(f"/api/soin/cas/{reste['id']}/cloture", headers=autre)
    assert soin.get(f"/api/soin/patients/{patient_id}/documents", headers=autre).status_code == 403
    assert soin.get(f"/api/soin/documents/{document_id}/pages/1", headers=autre).status_code == 403

    soin.post(f"/api/soin/cas/{cas.json()['cas_id']}/cloture", headers=medecin)
