"""Lire les Transcriptions relues (ADR 0010) : ce que soin et le carnet montrent d'un Document ancien.

Une Transcription est un `DocumentReference` de type Transcription (système des types de Document, code
`transcription`), son Markdown dans un `Binary` ; elle `transforms` le scan et `replaces` sa version
d'avant (ADR 0007). Seule sort de la relecture une version relue : courante, `docStatus` final, que nulle
autre courante ne remplace. Une version préliminaire ne se montre jamais ici.

Le service relecture les écrit (`commun.fhir.relecture`) ; ce module ne fait que les lire.
"""

import base64
from dataclasses import dataclass

from commun.fhir import systemes
from commun.fhir.client import ClientFhir, Ressource
from commun.fhir.dossier import id_de

CODE_TRANSCRIPTION = "transcription"


def est_une_transcription(ressource: Ressource) -> bool:
    return any(
        c.get("system") == systemes.TYPE_DE_DOCUMENT and c.get("code") == CODE_TRANSCRIPTION
        for c in ressource.get("type", {}).get("coding", [])
    )


def _cibles(ressource: Ressource, code: str) -> list[str]:
    return [
        cible
        for r in ressource.get("relatesTo", [])
        if r.get("code") == code and (cible := id_de(r.get("target")))
    ]


def scan_de(transcription: Ressource) -> str | None:
    """Le Document numérisé que la Transcription `transforms`."""
    return next(iter(_cibles(transcription, "transforms")), None)


def relues(trouvees: list[Ressource]) -> dict[str, Ressource]:
    """Parmi des DocumentReference, la Transcription relue de chaque scan : courante, finale, non
    remplacée par une autre version courante ; la plus récente quand il en reste plusieurs."""
    remplacees = {cible for r in trouvees for cible in _cibles(r, "replaces")}
    par_scan: dict[str, Ressource] = {}
    for r in trouvees:
        if not est_une_transcription(r) or r.get("status") != "current" or r.get("docStatus") != "final":
            continue
        scan = scan_de(r)
        if scan is None or r.get("id") in remplacees:
            continue
        deja = par_scan.get(scan)
        if deja is None or r.get("date", "") > deja.get("date", ""):
            par_scan[scan] = r
    return par_scan


async def transcription_relue(fhir: ClientFhir, scan: str) -> Ressource | None:
    """La Transcription relue du Document numérisé `scan`, ou None tant qu'il n'en a pas."""
    trouvees = await fhir.chercher(
        "DocumentReference", {"relatesto": f"DocumentReference/{scan}", "status": "current"}
    )
    return relues(trouvees).get(scan)


async def transcriptions_relues_du_patient(fhir: ClientFhir, patient: str) -> dict[str, Ressource]:
    """Toutes les Transcriptions relues du patient, par identifiant de leur scan : une seule recherche."""
    trouvees = await fhir.chercher(
        "DocumentReference",
        {
            "subject": f"Patient/{patient}",
            "status": "current",
            "type": f"{systemes.TYPE_DE_DOCUMENT}|{CODE_TRANSCRIPTION}",
        },
    )
    return relues(trouvees)


async def markdown_de(fhir: ClientFhir, transcription: Ressource) -> str | None:
    """Le Markdown d'une version de Transcription, lu dans son Binary."""
    url = next(iter(transcription.get("content", [])), {}).get("attachment", {}).get("url", "")
    binary = url.rsplit("/", 1)[-1]
    lu = await fhir.lire("Binary", binary) if binary else None
    return base64.b64decode(lu.get("data", "")).decode() if lu else None


@dataclass(frozen=True)
class TranscriptionLue:
    """Une Transcription relue, telle que soin et le carnet la reçoivent."""

    document_id: str
    """Le Document numérisé qu'elle transcrit."""
    markdown: str
    relue_le: str | None
    """L'instant où la version relue a été écrite, au Contrôle."""
    pages: int
    """Le nombre de pages du Document : ce vers quoi pointent les `page:N`."""


async def lire_transcription(fhir: ClientFhir, scan: Ressource, transcription: Ressource) -> TranscriptionLue | None:
    """La Transcription relue `transcription` du Document `scan`, avec son Markdown ; None si le Binary manque."""
    markdown = await markdown_de(fhir, transcription)
    if markdown is None:
        return None
    return TranscriptionLue(
        document_id=scan["id"],
        markdown=markdown,
        relue_le=transcription.get("date"),
        pages=len(scan.get("content", [])),
    )
