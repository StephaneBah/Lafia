"""Isolement réseau : ce que seul le réseau garantit, observé depuis les conteneurs et l'hôte.

Une application n'est que sur le réseau passerelle : elle ne joint pas le noyau, ni par son nom
ni par son adresse. Seule la passerelle publie des ports : HAPI n'est joignable que par un service.
"""

import json

import pytest

# Depuis un conteneur d'application : une requête HTTP obtient-elle une réponse, quelle qu'elle soit ?
# Code 0 : une réponse. Code 3 : aucune (nom inconnu, pas de route, délai écoulé).
# Tout autre code dit que la sonde n'a pas tourné, et ne prouve rien.
SONDE = (
    "fetch(process.argv[1], { signal: AbortSignal.timeout(3000) })"
    ".then(() => process.exit(0), () => process.exit(3))"
)
REPONSE, SANS_REPONSE = 0, 3


def sonder(docker, conteneur: str, url: str) -> int:
    return docker("compose", "exec", "-T", conteneur, "node", "-e", SONDE, url).returncode


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


@pytest.mark.parametrize("acteur", ["soin"])
def test_depuis_une_application_le_noyau_est_injoignable(docker, acteur):
    conteneur = f"application-{acteur}"
    # Témoin : depuis le même conteneur, la sonde obtient une réponse de la passerelle.
    # Sans lui, une sonde qui ne tourne pas passerait pour un noyau injoignable.
    assert sonder(docker, conteneur, "http://passerelle:8080/") == REPONSE

    assert sonder(docker, conteneur, "http://noyau:8080/fhir/metadata") == SANS_REPONSE
    for adresse in adresses_ip(docker, "noyau"):
        assert sonder(docker, conteneur, f"http://{adresse}:8080/fhir/metadata") == SANS_REPONSE


def test_seule_la_passerelle_publie_des_ports_sur_l_hote(docker):
    publies = ports_publies(docker)

    assert publies.pop("passerelle") == {80, 443}
    assert "noyau" in publies, "HAPI ne tourne pas : l'absence de port ne prouverait rien"
    assert publies == {service: set() for service in publies}
