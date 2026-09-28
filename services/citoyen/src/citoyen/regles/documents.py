"""Mes documents : les papiers numérisés du citoyen, tels que le carnet les montre
(`commun.fhir.documents.DocumentVu`, la même vue que soin et numerisation). Un citoyen ne voit que
les siens ; ceux d'un autre n'existent pas pour lui."""

from pydantic import BaseModel

from commun.fhir.client import Ressource
from commun.fhir.dossier import id_de
from commun.transcription import Volet, lire
from commun.transcription import par_etablissement as regrouper


def est_du_citoyen(document: Ressource | None, patient_id: str) -> bool:
    """Le Document est au dossier de ce citoyen."""
    return document is not None and id_de(document.get("subject")) == patient_id


# Les Transcriptions relues (ADR 0010) : chaque papier relu, recopié en volets, et tous les volets de
# tous les papiers regroupés par établissement. Rien n'est stocké par établissement : la vue se calcule.


class MaTranscription(BaseModel):
    """La Transcription relue d'un de mes documents."""

    markdown: str
    relue_le: str | None
    pages: int


class VoletLu(BaseModel):
    """Un volet d'une Transcription relue, et le Document dont il vient."""

    type: str
    date: str | None
    titre: str
    document_id: str
    pages: list[int]
    corps: str


class Etablissement(BaseModel):
    """Un établissement de mes anciens papiers, et ce qui s'y est passé, dans l'ordre des dates."""

    etablissement: str
    volets: list[VoletLu]


def par_etablissement(transcriptions: list[tuple[str, str]]) -> list[Etablissement]:
    """Les volets de toutes mes Transcriptions relues, `(identifiant du Document, Markdown)`, regroupés
    par établissement, chacun en ordre de date (`commun.transcription.par_etablissement`)."""
    source: dict[int, str] = {}
    volets: list[Volet] = []
    for document_id, markdown in transcriptions:
        for volet in lire(markdown).volets:
            source[id(volet)] = document_id
            volets.append(volet)
    return [
        Etablissement(
            etablissement=nom,
            volets=[
                VoletLu(
                    type=v.type,
                    date=v.date,
                    titre=v.titre,
                    document_id=source[id(v)],
                    pages=list(v.pages),
                    corps=v.corps,
                )
                for v in groupe
            ],
        )
        for nom, groupe in regrouper(volets).items()
    ]
