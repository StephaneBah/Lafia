"""Service soin, joint depuis son application : soin.<domaine>/api/soin/*."""


def test_sante_soin_rapporte_la_version_fhir_du_noyau(application):
    reponse = application("soin").get("/api/soin/sante")

    assert reponse.status_code == 200
    assert reponse.json() == {
        "service": "soin",
        "statut": "disponible",
        "noyau": {"statut": "disponible", "version_fhir": "4.0.1"},
    }


def test_documentation_openapi_de_soin_joignable_par_la_passerelle(application):
    soin = application("soin")

    contrat = soin.get("/api/soin/openapi.json")
    assert contrat.status_code == 200
    assert "/api/soin/sante" in contrat.json()["paths"]

    documentation = soin.get("/api/soin/docs")
    assert documentation.status_code == 200
    assert "/api/soin/openapi.json" in documentation.text
