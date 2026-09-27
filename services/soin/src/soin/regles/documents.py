"""Les Documents au service soin (ADR 0007, 0008) : ce qu'un soignant peut y ajouter, et d'où vient
chaque entrée qu'il écrit au dossier.

Une entrée saisie par le soignant est une déclaration ; reportée depuis un Document, c'est un report,
et ce Document doit être celui du même patient. Les entrées d'une visite sont relevées en visite.
"""

from commun.fhir.client import Ressource
from commun.fhir.documents import OCTETS_PAR_PAGE, PAGES_PAR_DOCUMENT, Origine, Page
from commun.fhir.dossier import id_de
from soin.regles.dossier import SaisieRefusee


class DocumentTropLourd(Exception):
    """Trop de pages, ou une page trop lourde (ADR 0008) : rien n'en est écrit."""


def origine_de_la_saisie(document_id: str | None) -> Origine:
    """`report` quand l'entrée est reportée depuis un Document, `declaration` sinon."""
    return "report" if document_id else "declaration"


def exiger_document_du_patient(document: Ressource | None, patient_id: str) -> None:
    """Un report ne se fait que depuis un Document du même patient : `SaisieRefusee` sinon."""
    if document is None or id_de(document.get("subject")) != patient_id:
        raise SaisieRefusee("ce document n'est pas au dossier de ce patient")


def verifier_limites(pages: list[Page]) -> None:
    """Au-delà des limites de l'ADR 0008 : `DocumentTropLourd` (413). Le format, lui, est vérifié à l'écriture (422)."""
    if len(pages) > PAGES_PAR_DOCUMENT or any(len(p.octets) > OCTETS_PAR_PAGE for p in pages):
        raise DocumentTropLourd(f"au plus {PAGES_PAR_DOCUMENT} pages de 3 Mo chacune")
