"""Mes documents : les papiers numérisés du citoyen, tels que le carnet les montre. Un citoyen ne
voit que les siens ; ceux d'un autre n'existent pas pour lui."""

from pydantic import BaseModel

from commun.fhir.client import Ressource
from commun.fhir.documents import document_vu, formats_des_pages
from commun.fhir.dossier import id_de


class DocumentLu(BaseModel):
    id: str
    type: str
    """Le type du papier : carnet, compte-rendu, resultat-analyse, ordonnance, imagerie, certificat, autre."""
    libelle: str
    annee: str | None
    etablissement: str | None
    """L'établissement d'origine, tel qu'il est écrit sur le papier."""
    pages: int
    formats: list[str]
    """Le format de chaque page : une image se montre, un PDF s'ouvre."""
    lisible: bool
    depose_le: str | None


def document_lu(ressource: Ressource) -> DocumentLu:
    vu = document_vu(ressource)
    return DocumentLu(
        id=vu.id,
        type=vu.type,
        libelle=vu.libelle_du_type,
        annee=vu.annee,
        etablissement=vu.etablissement,
        pages=vu.pages,
        formats=formats_des_pages(ressource),
        lisible=vu.lisibilite != "partiel",
        depose_le=vu.depose_le,
    )


def est_du_citoyen(document: Ressource | None, patient_id: str) -> bool:
    """Le Document est au dossier de ce citoyen."""
    return document is not None and id_de(document.get("subject")) == patient_id
