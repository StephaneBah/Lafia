"""Les Documents au service soin (ADR 0007, 0008) : d'où vient chaque entrée qu'un soignant écrit au
dossier. Ce qu'un Document admet se juge dans `commun.fhir.documents.valider_document`, comme au guichet.

Une entrée saisie par le soignant est une déclaration ; reportée depuis un Document, c'est un report,
et ce Document doit être celui du même patient. Les entrées d'une visite sont relevées en visite.
"""

from commun.fhir.client import Ressource
from commun.fhir.documents import Origine
from commun.fhir.dossier import id_de
from soin.regles.dossier import SaisieRefusee


def origine_de_la_saisie(document_id: str | None) -> Origine:
    """`report` quand l'entrée est reportée depuis un Document, `declaration` sinon."""
    return "report" if document_id else "declaration"


def exiger_document_du_patient(document: Ressource | None, patient_id: str) -> None:
    """Un report ne se fait que depuis un Document du même patient : `SaisieRefusee` sinon."""
    if document is None or id_de(document.get("subject")) != patient_id:
        raise SaisieRefusee("ce document n'est pas au dossier de ce patient")

