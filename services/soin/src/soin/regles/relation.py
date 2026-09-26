"""La relation de soin (ADR 0002) : ce qui ouvre un dossier à un soignant.

Elle tient tant que le patient a un cas de visite actif ouvert à l'établissement du soignant, ou
qui compte une visite à cet établissement. Ouvrir ou continuer un cas, le patient présent, l'établit.
"""

from commun.fhir.client import Ressource
from commun.fhir.dossier import id_de


def cas_de_l_etablissement(cas: Ressource, visites: list[Ressource], etablissement: str) -> bool:
    """`cas` est actif, et ouvert à `etablissement` ou y compte une visite."""
    if cas.get("status") != "active":
        return False
    if id_de(cas.get("managingOrganization")) == etablissement:
        return True
    return any(
        id_de(v.get("serviceProvider")) == etablissement
        and any(id_de(e) == cas["id"] for e in v.get("episodeOfCare", []))
        for v in visites
    )


def relation_de_soin(cas: list[Ressource], visites: list[Ressource], etablissement: str) -> bool:
    """Le soignant de `etablissement` a une relation de soin avec le patient de ces cas et visites."""
    return any(cas_de_l_etablissement(c, visites, etablissement) for c in cas)
