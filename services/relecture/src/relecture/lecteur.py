"""Le client du service extraction : le seul appel d'un service de Lafia à un autre (ADR 0009).

relecture envoie les pages d'un Document à `EXTRACTION_URL` (`http://extraction:8000/api/extraction`),
sur le réseau interne `extraction`, et reçoit une Extraction au contrat de `commun.extraction`. Rien
d'autre ne joint extraction, qui ne joint rien.
"""

import os

import httpx
from pydantic import ValidationError

from commun.extraction import DemandeDExtraction, Extraction

# Un modèle réel lira jusqu'à 20 pages : il a le temps qu'il faut, pas davantage.
DELAI_SECONDES = 120.0


class ExtractionIndisponible(Exception):
    """extraction n'a pas répondu, ou pas par une Extraction au contrat."""


class Lecteur:
    def __init__(self, url_base: str) -> None:
        self._url_base = url_base

    @classmethod
    def depuis_environnement(cls) -> "Lecteur":
        url_base = os.environ.get("EXTRACTION_URL")
        if not url_base:
            raise RuntimeError("EXTRACTION_URL manquante : adresse du service extraction.")
        return cls(url_base)

    async def extraire(self, demande: DemandeDExtraction) -> Extraction:
        try:
            async with httpx.AsyncClient(base_url=self._url_base, timeout=DELAI_SECONDES) as http:
                reponse = await http.post("extraire", json=demande.model_dump())
        except httpx.HTTPError as erreur:
            raise ExtractionIndisponible(type(erreur).__name__) from erreur
        if reponse.is_error:
            raise ExtractionIndisponible(f"statut {reponse.status_code}")
        try:
            return Extraction.model_validate(reponse.json())
        except (ValueError, ValidationError) as erreur:
            # Le nom de l'erreur seulement : son message citerait ce que le modèle a lu.
            raise ExtractionIndisponible(f"réponse hors contrat : {type(erreur).__name__}") from erreur


def lecteur() -> Lecteur:
    """Dépendance FastAPI : le client du service extraction, à l'adresse de `EXTRACTION_URL`."""
    return Lecteur.depuis_environnement()
