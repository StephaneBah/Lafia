"""Isolement réseau : ce que seul le réseau garantit, observé depuis les conteneurs et l'hôte.

Les applications et identite ne sont que sur le réseau passerelle : ils ne joignent pas le noyau,
ni par son nom ni par son adresse. Seule la passerelle publie des ports : HAPI n'est joignable que
par un service qui parle FHIR.
"""

import json

import pytest

# Depuis un conteneur : une requête HTTP obtient-elle une réponse, quelle qu'elle soit ?
# Code 0 : une réponse. Code 3 : aucune (nom inconnu, pas de route, délai écoulé).
# Tout autre code dit que la sonde n'a pas tourné, et ne prouve rien.
# Chaque conteneur a la sonde de l'interpréteur qu'il embarque.
SONDE_NODE = [
    "node",
    "-e",
    "fetch(process.argv[1], { signal: AbortSignal.timeout(3000) })"
    ".then(() => process.exit(0), () => process.exit(3))",
]
SONDE_PYTHON = [
    "python",
    "-c",
    "import sys, urllib.error, urllib.request\n"
    "try: urllib.request.urlopen(sys.argv[1], timeout=3)\n"
    "except urllib.error.HTTPError: pass\n"
    "except OSError: sys.exit(3)",
]
REPONSE, SANS_REPONSE = 0, 3

# Les conteneurs hors du réseau noyau, et leur sonde.
HORS_DU_NOYAU = {
    "application-soin": SONDE_NODE,
    "application-caisse": SONDE_NODE,
    "application-pharmacie": SONDE_NODE,
    "application-citoyen": SONDE_NODE,
    "identite": SONDE_PYTHON,
}


def sonder(docker, conteneur: str, url: str) -> int:
    return docker("compose", "exec", "-T", conteneur, *HORS_DU_NOYAU[conteneur], url).returncode


def adresses_ip(docker, service: str) -> list[str]:
    identifiant = docker("compose", "ps", "--quiet", service).stdout.strip()
    assert identifiant, f"{service} ne tourne pas"
    inspection = docker(
        "inspect", "--format", "{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}", identifiant
    )
    return inspection.stdout.split()


def ports_publies(docker) -> dict[str, set[int]]:
    """Pour chaque conteneur de la pile en marche, les ports qu'il publie sur l'hôte."""
    conteneurs = docker("compose", "ps", "--format", "json").stdout.splitlines()
    publies: dict[str, set[int]] = {}
    for ligne in conteneurs:
        conteneur = json.loads(ligne)
        publies[conteneur["Service"]] = {
            publication["PublishedPort"]
            for publication in conteneur["Publishers"] or []
            if publication["PublishedPort"]
        }
    return publies


@pytest.mark.parametrize("conteneur", HORS_DU_NOYAU)
def test_hors_du_reseau_noyau_le_noyau_est_injoignable(docker, conteneur):
    # Témoin : depuis le même conteneur, la sonde obtient une réponse de la passerelle.
    # Sans lui, une sonde qui ne tourne pas passerait pour un noyau injoignable.
    assert sonder(docker, conteneur, "http://passerelle:8080/") == REPONSE

    assert sonder(docker, conteneur, "http://noyau:8080/fhir/metadata") == SANS_REPONSE
    for adresse in adresses_ip(docker, "noyau"):
        assert sonder(docker, conteneur, f"http://{adresse}:8080/fhir/metadata") == SANS_REPONSE


def test_le_chargement_n_est_que_sur_le_reseau_noyau(docker):
    # Il s'est arrêté après avoir chargé le jeu : `--all` le trouve quand même.
    identifiant = docker("compose", "ps", "--all", "--quiet", "chargement").stdout.strip()
    assert identifiant, "chargement n'a pas tourné"
    inspection = docker("inspect", "--format", "{{json .NetworkSettings.Networks}}", identifiant)

    assert set(json.loads(inspection.stdout)) == {"lafia_noyau"}


def test_seule_la_passerelle_publie_des_ports_sur_l_hote(docker):
    publies = ports_publies(docker)

    assert publies.pop("passerelle") == {80, 443}
    assert "noyau" in publies, "HAPI ne tourne pas : l'absence de port ne prouverait rien"
    assert publies == {service: set() for service in publies}
