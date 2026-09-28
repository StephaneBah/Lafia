"""Le guichet de numérisation : l'agent ouvre un Dépôt sur un NPI et une pièce d'identité, ne voit du
patient que son nom et son année de naissance, numérise ses papiers en Documents, les revoit, puis clôt
le Dépôt. Seul l'agent qui l'a ouvert s'en sert, et plus rien n'y entre après la clôture.
"""

import struct
import zlib
from datetime import date

import pytest

from conftest import jeton_pose

DEPOTS = "/api/numerisation/depots"
ORIGINE = "https://lafia.bj/fhir/CodeSystem/origine"
DEPOT = "https://lafia.bj/fhir/identifiant/depot"
PAPIER_ABIME = "https://lafia.bj/fhir/StructureDefinition/papier-abime"


def _porteur(jeton: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {jeton}"}


def _png() -> bytes:
    """Une image PNG valide d'un pixel, faite ici : aucun papier réel n'entre dans la suite."""

    def morceau(type_: bytes, donnees: bytes) -> bytes:
        return struct.pack(">I", len(donnees)) + type_ + donnees + struct.pack(">I", zlib.crc32(type_ + donnees))

    entete = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + morceau(b"IHDR", entete)
        + morceau(b"IDAT", zlib.compress(b"\x00\xff\xff\xff"))
        + morceau(b"IEND", b"")
    )


PAGE = _png()
CARNET_DE_2019 = {"type": "carnet", "annee": "2019", "lisibilite": "lisible", "etablissement": "CS de Kpanroun"}


def _compte(comptes, etablissement: str):
    return next(
        c for c in comptes if c.role == "agent de numérisation" and c.etablissement == etablissement and not c.reserve_aux_tests
    )


@pytest.fixture(scope="module")
def agent(comptes, connecter) -> dict[str, str]:
    """L'agent de numérisation du guichet du CNHU."""
    return _porteur(jeton_pose(connecter(_compte(comptes, "cnhu-hkm"))))


@pytest.fixture(scope="module")
def autre_agent(comptes, connecter) -> dict[str, str]:
    """L'agent de numérisation du centre de santé de Kpanroun."""
    return _porteur(jeton_pose(connecter(_compte(comptes, "cs-kpanroun"))))


@pytest.fixture(scope="module")
def patient(jeu) -> dict:
    return next(p for p in jeu("patients")["patient"] if not p.get("reserve_aux_tests"))


@pytest.fixture
def numerisation(application):
    return application("numerisation")


def _ouvrir(numerisation, agent, npi: str, piece: str = "cni", reprise: bool = True):
    return numerisation.post(DEPOTS, json={"npi": npi, "piece": piece, "reprise": reprise}, headers=agent)


def _deposer(numerisation, agent, depot: str, pages: list[tuple[str, bytes, str]], champs=CARNET_DE_2019):
    return numerisation.post(
        f"{DEPOTS}/{depot}/documents",
        data=champs,
        files=[("pages", fichier) for fichier in pages],
        headers=agent,
    )


def test_le_guichet_numerise_un_carnet_le_revoit_puis_clot_le_depot(numerisation, agent, patient):
    ouverture = _ouvrir(numerisation, agent, patient["npi"])

    assert ouverture.status_code == 201, ouverture.text
    corps = ouverture.json()
    depot = corps["depot_id"]
    # Le nom et l'année de naissance, à comparer à la pièce : ni le NPI, ni rien du dossier.
    identite = {
        "nom": patient["nom"],
        "prenoms": " ".join(patient["prenoms"]),
        "annee_de_naissance": str(patient["naissance"].year),
    }
    assert corps == {"depot_id": depot, "patient": identite}
    assert patient["npi"] not in ouverture.text

    depose = _deposer(numerisation, agent, depot, [("page-1.png", PAGE, "image/png")])
    assert depose.status_code == 201, depose.text
    document = depose.json()["document_id"]
    assert depose.json() == {"document_id": document, "pages": 1}

    lu = numerisation.get(f"{DEPOTS}/{depot}", headers=agent)
    assert lu.status_code == 200, lu.text
    assert lu.json()["patient"] == identite
    # La vue d'un Document que soin et citoyen rendent aussi.
    (vu,) = lu.json()["documents"]
    assert vu == {
        "id": document,
        "type": "carnet",
        "libelle": "Carnet de santé",
        "annee": "2019",
        "etablissement": "CS de Kpanroun",
        "lisibilite": "lisible",
        "pages": 1,
        "formats": ["image/png"],
        "origine": "numerisation",
        "depose_le": vu["depose_le"],
        "papier_abime": None,
    }

    page = numerisation.get(f"{DEPOTS}/{depot}/documents/{document}/pages/1", headers=agent)
    assert page.status_code == 200
    assert page.headers["content-type"] == "image/png"
    assert page.headers["x-content-type-options"] == "nosniff"
    assert page.content == PAGE
    assert numerisation.get(f"{DEPOTS}/{depot}/documents/{document}/pages/2", headers=agent).status_code == 404

    cloture = numerisation.post(f"{DEPOTS}/{depot}/cloture", headers=agent)
    assert cloture.status_code == 200, cloture.text

    # Clos : plus rien n'y entre, plus rien ne s'y lit.
    assert _deposer(numerisation, agent, depot, [("page-2.png", PAGE, "image/png")]).status_code == 409
    assert numerisation.get(f"{DEPOTS}/{depot}", headers=agent).status_code == 409
    assert numerisation.post(f"{DEPOTS}/{depot}/cloture", headers=agent).status_code == 409


def test_le_depot_clos_est_dans_le_noyau_document_et_provenance(numerisation, agent, patient, compte_de, noyau):
    depot = _ouvrir(numerisation, agent, patient["npi"], piece="passeport").json()["depot_id"]
    document = _deposer(numerisation, agent, depot, [("page-1.png", PAGE, "image/png")] * 2).json()["document_id"]
    assert numerisation.post(f"{DEPOTS}/{depot}/cloture", headers=agent).status_code == 200

    reference, provenances = noyau([f"DocumentReference/{document}", f"Provenance?_tag={DEPOT}|{depot}"])

    ressource = reference.ressource
    assert ressource["subject"] == {"reference": f"Patient/{patient['id']}"}
    assert ressource["author"] == [{"reference": f"Practitioner/{compte_de('agent de numérisation').sub}"}]
    assert ressource["context"]["period"]["start"] == "2019"
    assert [c["attachment"]["title"] for c in ressource["content"]] == ["Page 1", "Page 2"]
    assert {(e["system"], e["code"]) for e in ressource["meta"]["tag"]} >= {(ORIGINE, "numerisation"), (DEPOT, depot)}
    (provenance,) = [e["resource"] for e in provenances.ressource.get("entry", [])]
    assert provenance["target"] == [{"reference": f"DocumentReference/{document}"}]
    assert {(e["system"], e["code"]) for e in provenance["meta"]["tag"]} == {
        (DEPOT, depot), (ORIGINE, "numerisation"), (ORIGINE, "reprise")
    }
    (motif,) = provenance["reason"]
    assert motif["coding"] == [
        {"system": "https://lafia.bj/fhir/CodeSystem/piece-d-identite", "code": "passeport", "display": "Passeport"}
    ]
    assert "Passeport" in motif["text"]


def test_un_depot_ne_sert_qu_a_l_agent_qui_l_a_ouvert(numerisation, agent, autre_agent, patient):
    depot = _ouvrir(numerisation, agent, patient["npi"]).json()["depot_id"]

    assert numerisation.get(f"{DEPOTS}/{depot}", headers=autre_agent).status_code == 403
    assert _deposer(numerisation, autre_agent, depot, [("page.png", PAGE, "image/png")]).status_code == 403
    assert numerisation.post(f"{DEPOTS}/{depot}/cloture", headers=autre_agent).status_code == 403
    # L'agent qui l'a ouvert s'en sert toujours.
    assert numerisation.get(f"{DEPOTS}/{depot}", headers=agent).status_code == 200


def test_un_soignant_n_ouvre_pas_de_depot(numerisation, jeton_de, patient):
    assert _ouvrir(numerisation, _porteur(jeton_de("médecin")), patient["npi"]).status_code == 403


def test_un_npi_inconnu_ou_un_depot_inconnu_repond_404(numerisation, agent, jeu):
    connus = {p["npi"] for p in jeu("patients")["patient"]}
    inconnu = next(f"000000{n:07d}" for n in range(1, 10_000_000) if f"000000{n:07d}" not in connus)

    assert _ouvrir(numerisation, agent, inconnu).status_code == 404
    assert numerisation.get(f"{DEPOTS}/depot-inconnu", headers=agent).status_code == 404


def test_une_piece_d_identite_inconnue_est_refusee(numerisation, agent, patient):
    assert _ouvrir(numerisation, agent, patient["npi"], piece="carte-de-visite").status_code == 422


@pytest.mark.parametrize(
    ("pages", "champs", "statut"),
    [
        pytest.param([("page.jpg", PAGE, "image/jpeg")], CARNET_DE_2019, 422, id="format annoncé autre que le contenu"),
        pytest.param([("page.txt", b"du texte", "text/plain")], CARNET_DE_2019, 422, id="format refusé"),
        pytest.param([("page.png", PAGE, "image/png")], {**CARNET_DE_2019, "type": "radio"}, 422, id="type inconnu"),
        pytest.param([("page.png", PAGE, "image/png")], {**CARNET_DE_2019, "annee": "19"}, 422, id="année mal écrite"),
        pytest.param(
            [("page.png", PAGE, "image/png")], {**CARNET_DE_2019, "annee": str(date.today().year + 1)}, 422, id="année à venir"
        ),
        pytest.param([("page.png", PAGE, "image/png")], {**CARNET_DE_2019, "annee": "1899"}, 422, id="année avant 1900"),
        pytest.param([], CARNET_DE_2019, 422, id="aucune page"),
        pytest.param([("page.png", PAGE, "image/png")] * 21, CARNET_DE_2019, 413, id="plus de 20 pages"),
        pytest.param(
            [("page.png", PAGE + b"\x00" * (3 * 1024 * 1024), "image/png")], CARNET_DE_2019, 413, id="page de plus de 3 Mo"
        ),
    ],
)
def test_un_document_hors_des_limites_est_refuse(numerisation, agent, patient, pages, champs, statut):
    depot = _ouvrir(numerisation, agent, patient["npi"]).json()["depot_id"]

    assert _deposer(numerisation, agent, depot, pages, champs).status_code == statut
    assert numerisation.get(f"{DEPOTS}/{depot}", headers=agent).json()["documents"] == []


NOTE_DE_PAPIER_ABIME = "Coin déchiré et encre passée : le papier ne se lit pas mieux."


def _deposer_un_papier_abime(numerisation, agent, patient) -> tuple[str, str]:
    depot = _ouvrir(numerisation, agent, patient["npi"]).json()["depot_id"]
    depose = _deposer(
        numerisation, agent, depot, [("page-1.png", PAGE, "image/png")], {**CARNET_DE_2019, "papier_abime": NOTE_DE_PAPIER_ABIME}
    )
    assert depose.status_code == 201, depose.text
    return depot, depose.json()["document_id"]


def test_un_papier_abime_garde_sa_note_et_le_depot_la_montre(numerisation, agent, patient):
    """Une page qu'un papier abîmé en lui-même empêche de réussir la capture se garde, avec la note de l'agent."""
    depot, _ = _deposer_un_papier_abime(numerisation, agent, patient)

    (vu,) = numerisation.get(f"{DEPOTS}/{depot}", headers=agent).json()["documents"]
    assert vu["papier_abime"] == NOTE_DE_PAPIER_ABIME


def test_la_note_de_papier_abime_est_une_extension_du_document(numerisation, agent, patient, noyau):
    _, document = _deposer_un_papier_abime(numerisation, agent, patient)

    (reference,) = noyau([f"DocumentReference/{document}"])
    assert {"url": PAPIER_ABIME, "valueString": NOTE_DE_PAPIER_ABIME} in reference.ressource["extension"]


def test_une_note_de_papier_abime_de_plus_de_300_caracteres_est_refusee(numerisation, agent, patient):
    depot = _ouvrir(numerisation, agent, patient["npi"]).json()["depot_id"]

    refuse = _deposer(numerisation, agent, depot, [("page-1.png", PAGE, "image/png")], {**CARNET_DE_2019, "papier_abime": "x" * 301})

    assert refuse.status_code == 422
    assert numerisation.get(f"{DEPOTS}/{depot}", headers=agent).json()["documents"] == []
