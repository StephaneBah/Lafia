"""Lire les Transcriptions relues (ADR 0010) : ce que soin et le carnet montrent d'un Document ancien.

Le service relecture les écrit, et `commun.fhir.relecture` dit leur forme : `transcription_relue` trouve
celle d'un scan, `markdown_de` en lit le texte. Ce module y ajoute ce que soin et le carnet demandent en
plus : toutes les Transcriptions relues d'un patient en une recherche, et la vue qu'on en rend. Seule une
version relue sort de la relecture : courante, `docStatus` final. Une version préliminaire, jamais.
"""

from dataclasses import dataclass

from commun.fhir import systemes
from commun.fhir.client import ClientFhir, Ressource
from commun.fhir.dossier import id_de
from commun.fhir.relecture import est_une_transcription, markdown_de


def scan_de(transcription: Ressource) -> str | None:
    """Le Document numérisé que la Transcription `transforms`."""
    return next(
        (id_ for r in transcription.get("relatesTo", []) if r.get("code") == "transforms" and (id_ := id_de(r.get("target")))),
        None,
    )


async def transcriptions_relues_du_patient(fhir: ClientFhir, patient: str) -> dict[str, Ressource]:
    """Toutes les Transcriptions relues du patient, par identifiant de leur scan, en une seule recherche ;
    la plus récente par scan, comme `commun.fhir.relecture.transcription_relue`."""
    trouvees = await fhir.chercher(
        "DocumentReference",
        {"subject": f"Patient/{patient}", "status": "current", "type": f"{systemes.TYPE_DE_DOCUMENT}|transcription"},
    )
    par_scan: dict[str, Ressource] = {}
    for version in trouvees:
        scan = scan_de(version)
        if scan is None or not est_une_transcription(version) or version.get("docStatus") != "final":
            continue
        if version.get("date", "") >= par_scan.get(scan, {}).get("date", ""):
            par_scan[scan] = version
    return par_scan


@dataclass(frozen=True)
class TranscriptionLue:
    """Une Transcription relue, telle que soin et le carnet la reçoivent."""

    markdown: str
    relue_le: str | None
    """L'instant de la version relue, écrite au Contrôle."""
    pages: int
    """Le nombre de pages du Document : ce vers quoi pointent les `page:N`."""


async def lire_transcription(fhir: ClientFhir, scan: Ressource, version: Ressource) -> TranscriptionLue | None:
    """La version relue `version` du Document `scan`, avec son Markdown ; None si son Binary manque."""
    markdown = await markdown_de(fhir, version)
    if markdown is None:
        return None
    return TranscriptionLue(markdown=markdown, relue_le=version.get("date"), pages=len(scan.get("content", [])))
