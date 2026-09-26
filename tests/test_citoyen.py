"""Acteur citoyen : ce qui lui est propre. Son jeton porte son NPI, que ni son service ni son application ne lui renvoient.

Ce qu'il partage avec les autres acteurs se vérifie dans tests/test_acteurs.py ; sa connexion, dans
tests/test_identite.py.
"""


def test_session_rend_le_citoyen_connecte_sans_son_npi(application, jeton_de, citoyen_de_demonstration, transport):
    reponse = application("citoyen").get("/api/citoyen/session", headers=transport(jeton_de("citoyen")))

    assert reponse.status_code == 200
    assert set(reponse.json()) == {"sub", "role"}
    assert reponse.json()["role"] == "citoyen"
    assert citoyen_de_demonstration.npi not in reponse.text


def test_application_affiche_le_citoyen_connecte_sans_jamais_son_npi(
    page, html_de_page, jeton_de, citoyen_de_demonstration
):
    jeton = jeton_de("citoyen")

    # Témoin : la page a reçu la session. Sans elle, l'absence du NPI ne prouverait rien.
    assert "Connecté comme citoyen" in page("citoyen", jeton=jeton)
    # Nulle part dans la réponse : ni dans le texte affiché, ni dans les balises, ni dans les scripts.
    assert citoyen_de_demonstration.npi not in html_de_page("citoyen", jeton=jeton)
