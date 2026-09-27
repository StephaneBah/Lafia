"""Lire les pages d'un Document téléversé en multipart, pour numerisation comme pour soin (ADR 0008).

La lecture ne décide de rien : elle rend ce qui est arrivé, sans jamais lire plus que de quoi savoir
qu'une limite est dépassée. `commun.fhir.documents.valider_document` juge ensuite.
"""

from fastapi import UploadFile

from commun.fhir.documents import OCTETS_PAR_PAGE, PAGES_PAR_DOCUMENT, Page


def format_declare(type_de_contenu: str | None) -> str:
    """Le format déclaré d'un fichier, sans ses paramètres : `image/jpeg; charset=x` donne `image/jpeg`."""
    return (type_de_contenu or "").split(";", 1)[0].strip().lower()


async def pages_televersees(fichiers: list[UploadFile]) -> list[Page]:
    """Les pages reçues, dans l'ordre. Une page de plus que la limite, et un octet de plus que la limite
    d'une page, suffisent à savoir qu'un Document la dépasse : le reste n'est pas lu."""
    return [
        Page(format=format_declare(fichier.content_type), octets=await fichier.read(OCTETS_PAR_PAGE + 1))
        for fichier in fichiers[: PAGES_PAR_DOCUMENT + 1]
    ]
