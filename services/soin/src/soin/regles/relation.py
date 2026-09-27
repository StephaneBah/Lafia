"""La relation de soin (ADR 0002) : ce qui ouvre un dossier à un soignant.

Elle tient tant que le patient a un cas de visite actif ouvert à l'établissement du soignant, ou
qui compte une visite à cet établissement. Ouvrir ou continuer un cas, le patient présent, l'établit.
Quand elle ne tient que par un cas d'accès d'urgence, chaque lecture est tracée `acces-urgence`.
"""

from commun.fhir import soin as fhir_soin
from commun.fhir.client import Ressource
from commun.fhir.dossier import Motif


class SansRelationDeSoin(Exception):
    """Le soignant n'a pas de relation de soin avec ce patient, ou avec ce cas."""


def cas_de_l_etablissement(cas: Ressource, visites: list[Ressource], etablissement: str) -> bool:
    """`cas` est actif, et ouvert à `etablissement` ou y compte une visite."""
    if not fhir_soin.cas_actif(cas):
        return False
    if fhir_soin.etablissement_du_cas(cas) == etablissement:
        return True
    return any(
        fhir_soin.etablissement_de_la_visite(v) == etablissement and cas["id"] in fhir_soin.cas_de_la_visite(v)
        for v in visites
    )


def cas_d_urgence(cas: Ressource, visites: list[Ressource]) -> bool:
    """`cas` a été ouvert par un accès d'urgence : il compte une visite d'urgence."""
    return any(fhir_soin.visite_d_urgence(v) and cas["id"] in fhir_soin.cas_de_la_visite(v) for v in visites)


def motif_de_la_relation(cas: list[Ressource], visites: list[Ressource], etablissement: str) -> Motif | None:
    """`relation-de-soin` si un cas ordinaire la fonde, `acces-urgence` si seul un cas d'urgence
    ouvert la fonde, None sans relation de soin."""
    fondateurs = [c for c in cas if cas_de_l_etablissement(c, visites, etablissement)]
    if not fondateurs:
        return None
    if all(cas_d_urgence(c, visites) for c in fondateurs):
        return "acces-urgence"
    return "relation-de-soin"


def relation_de_soin(cas: list[Ressource], visites: list[Ressource], etablissement: str) -> bool:
    """Le soignant de `etablissement` a une relation de soin avec le patient de ces cas et visites."""
    return motif_de_la_relation(cas, visites, etablissement) is not None


def exiger_relation(
    cas: list[Ressource], visites: list[Ressource], etablissement: str, *, avec_le_cas: str | None = None
) -> Motif:
    """Le motif sous lequel tracer l'accès ; `SansRelationDeSoin` sans relation de soin.

    Avec `avec_le_cas`, la relation doit tenir par ce cas-là : il est actif, et ouvert à
    `etablissement` ou y compte une visite.
    """
    if avec_le_cas is not None:
        le_cas = next((c for c in cas if c["id"] == avec_le_cas), None)
        if le_cas is None or not cas_de_l_etablissement(le_cas, visites, etablissement):
            raise SansRelationDeSoin()
        return "acces-urgence" if cas_d_urgence(le_cas, visites) else "relation-de-soin"
    motif = motif_de_la_relation(cas, visites, etablissement)
    if motif is None:
        raise SansRelationDeSoin()
    return motif
