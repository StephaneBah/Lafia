"""Le contrat de l'Extraction (ADR 0009) : ce que le service `relecture` envoie, ce que `extraction` rend.

Le modèle de lecture n'existe pas encore ; celui qui le construira répond à ce contrat, et rien d'autre ne
change. Aujourd'hui, un service de démonstration y répond avec des propositions fixes.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

FormatDePage = Literal["image/jpeg", "image/png", "application/pdf"]


class PageAExtraire(BaseModel):
    format: FormatDePage
    octets: str
    """Les octets de la page, en base64."""


class DemandeDExtraction(BaseModel):
    document_id: str
    """L'identifiant du DocumentReference lu, pour les journaux techniques seulement."""
    type_de_document: str
    pages: list[PageAExtraire] = Field(min_length=1, max_length=20)


class Modele(BaseModel):
    nom: str
    version: str


class Proposition(BaseModel):
    """Un fait que le modèle croit lire : une ressource FHIR sans id, sans sujet, sans auteur."""

    ressource: dict[str, Any]
    confiance: float = Field(ge=0, le=1)
    extrait: str | None = None
    """Le passage du texte où le modèle l'a lu, pour que le soignant le retrouve sur la page."""


class Extraction(BaseModel):
    modele: Modele
    texte: str
    """Le texte brut lu, page après page."""
    transcription: str = ""
    """Le brouillon de Transcription, en Markdown restreint par volets (ADR 0010) : ce que les
    agents de relecture corrigent. Vide quand le modèle ne sait pas structurer."""
    propositions: list[Proposition]


MODELE_DE_DEMONSTRATION = Modele(nom="demonstration", version="0")
"""Le modèle que sert l'Extraction de démonstration ; chaque écran le signale."""

TYPES_DE_PROPOSITION = frozenset({"Observation", "Condition", "AllergyIntolerance", "MedicationStatement"})
"""Ce qu'une Extraction peut proposer : les entrées que le dossier tient déjà (ADR 0009)."""
