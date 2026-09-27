"""Mes documents : les papiers numérisés du citoyen, tels que le carnet les montre
(`commun.fhir.documents.DocumentVu`, la même vue que soin et numerisation). Un citoyen ne voit que
les siens ; ceux d'un autre n'existent pas pour lui."""

from commun.fhir.client import Ressource
from commun.fhir.dossier import id_de


def est_du_citoyen(document: Ressource | None, patient_id: str) -> bool:
    """Le Document est au dossier de ce citoyen."""
    return document is not None and id_de(document.get("subject")) == patient_id
