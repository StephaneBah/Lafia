"""Acteur citoyen : ce qui lui est propre. Son jeton porte son NPI, que ni son service ni son application ne lui renvoient.

Ce qu'il partage avec les autres acteurs se vérifie dans tests/test_acteurs.py.
"""

NPI = "0000000042"


def test_session_rend_le_citoyen_du_jeton_sans_son_npi(application, signer_jeton, transport):
    jeton = signer_jeton("citoyen", sub="citoyen-test-7", npi=NPI)

    reponse = application("citoyen").get("/api/citoyen/session", headers=transport(jeton))

    assert reponse.status_code == 200
    assert reponse.json() == {"sub": "citoyen-test-7", "role": "citoyen"}


def test_application_affiche_le_citoyen_connecte_sans_jamais_son_npi(page, html_de_page, signer_jeton):
    jeton = signer_jeton("citoyen", npi=NPI)

    # Témoin : la page a reçu la session. Sans elle, l'absence du NPI ne prouverait rien.
    assert "Connecté comme citoyen" in page("citoyen", jeton=jeton)
    # Nulle part dans la réponse : ni dans le texte affiché, ni dans les balises, ni dans les scripts.
    assert NPI not in html_de_page("citoyen", jeton=jeton)
