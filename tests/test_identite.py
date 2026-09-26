"""Service identite : joint depuis le sous-domaine de chaque application, sous /api/identite/*."""

import pytest


@pytest.mark.parametrize("acteur", ["soin", "caisse", "pharmacie"])
def test_sante_identite_joignable_depuis_le_sous_domaine_d_une_application(application, acteur):
    reponse = application(acteur).get("/api/identite/sante")

    assert reponse.status_code == 200
    assert reponse.json() == {"service": "identite", "statut": "disponible"}
