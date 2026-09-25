"""Acteur soin : son application sur soin.<domaine>, son service sous soin.<domaine>/api/soin/*."""

from html.parser import HTMLParser


# Balises dont le contenu n'apparaît pas dans la page affichée.
BALISES_INVISIBLES = {"title", "script", "style", "template"}


class _LecteurDeTexteVisible(HTMLParser):
    """Recueille le texte qu'un lecteur voit dans la page : ni balises, ni commentaires, ni scripts."""

    def __init__(self) -> None:
        super().__init__()
        self.morceaux: list[str] = []
        self._dans_une_balise_invisible = 0

    def handle_starttag(self, tag: str, attrs: object) -> None:
        if tag in BALISES_INVISIBLES:
            self._dans_une_balise_invisible += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in BALISES_INVISIBLES and self._dans_une_balise_invisible:
            self._dans_une_balise_invisible -= 1

    def handle_data(self, data: str) -> None:
        if not self._dans_une_balise_invisible:
            self.morceaux.append(data)


def texte_visible(html: str) -> str:
    lecteur = _LecteurDeTexteVisible()
    lecteur.feed(html)
    return " ".join(" ".join(lecteur.morceaux).split())


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


def test_application_soin_affiche_son_service_et_la_version_fhir_du_noyau(application):
    page = application("soin").get("/")

    assert page.status_code == 200
    assert page.headers["content-type"].startswith("text/html")
    texte = texte_visible(page.text)
    assert "Soin" in texte
    assert "Service soin disponible" in texte
    assert "Noyau disponible, FHIR 4.0.1" in texte
