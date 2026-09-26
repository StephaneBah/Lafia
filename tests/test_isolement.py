"""Isolement réseau : ce que seul le réseau garantit, observé depuis les conteneurs et l'hôte.

Les applications et identite ne sont pas sur le réseau noyau : ils ne joignent pas le noyau, ni par
son nom ni par son adresse. La base d'identite n'est que sur le réseau identite : aucune application,
aucun service qui parle FHIR ne la joint. Seule la passerelle publie des ports : HAPI n'est joignable
que par un service qui parle FHIR.
"""

import json

import pytest

# Depuis un conteneur : une requête HTTP obtient-elle une réponse, quelle qu'elle soit ?
# Code 0 : une réponse. Code 3 : aucune (nom inconnu, pas de route, délai écoulé).
# Tout autre code dit que la sonde n'a pas tourné, et ne prouve rien.
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
# Une base ne parle pas HTTP : une connexion TCP ouverte suffit à dire qu'elle est joignable.
SONDE_TCP_NODE = [
    "node",
    "-e",
    "require('node:net').connect(Number(process.argv[2]), process.argv[1])"
    ".setTimeout(3000, () => process.exit(3))"
    ".on('connect', () => process.exit(0)).on('error', () => process.exit(3))",
]
SONDE_TCP_PYTHON = [
    "python",
    "-c",
    "import socket, sys\n"
    "try: socket.create_connection((sys.argv[1], int(sys.argv[2])), timeout=3)\n"
    "except OSError: sys.exit(3)",
]
REPONSE, SANS_REPONSE = 0, 3

APPLICATIONS = ["application-soin", "application-caisse", "application-pharmacie", "application-citoyen"]
SERVICES_FHIR = ["soin", "caisse", "pharmacie", "citoyen"]

# Chaque conteneur a les sondes de l'interpréteur qu'il embarque : HTTP, puis TCP.
SONDES = {
    **{application: (SONDE_NODE, SONDE_TCP_NODE) for application in APPLICATIONS},
    **{service: (SONDE_PYTHON, SONDE_TCP_PYTHON) for service in [*SERVICES_FHIR, "identite"]},
}

# Les conteneurs hors du réseau noyau.
HORS_DU_NOYAU = [*APPLICATIONS, "identite"]
# Les conteneurs hors du réseau identite : tout ce qui pourrait vouloir lire les comptes.
HORS_D_IDENTITE = [*APPLICATIONS, *SERVICES_FHIR]


def sonder(docker, conteneur: str, url: str) -> int:
    sonde_http, _ = SONDES[conteneur]
    return docker("compose", "exec", "-T", conteneur, *sonde_http, url).returncode


def sonder_tcp(docker, conteneur: str, hote: str, port: int) -> int:
    _, sonde_tcp = SONDES[conteneur]
    return docker("compose", "exec", "-T", conteneur, *sonde_tcp, hote, str(port)).returncode


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


@pytest.mark.parametrize("conteneur", HORS_D_IDENTITE)
def test_hors_du_reseau_identite_la_base_d_identite_est_injoignable(docker, conteneur):
    # Témoin : identite, lui, la joint. Sans lui, une sonde qui ne tourne pas passerait pour une base injoignable.
    assert sonder_tcp(docker, "identite", "base-identite", 5432) == REPONSE

    assert sonder_tcp(docker, conteneur, "base-identite", 5432) == SANS_REPONSE
    for adresse in adresses_ip(docker, "base-identite"):
        assert sonder_tcp(docker, conteneur, adresse, 5432) == SANS_REPONSE


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
