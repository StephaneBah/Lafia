"""Ce que la pharmacie décide d'une ordonnance : quelles lignes elle remet, où elle en est de chacune,
quelle allergie l'arrête, et si une délivrance demandée peut s'écrire.

Règles pures : elles ne lisent pas le noyau. `pharmacie.ordonnance` leur donne ce qu'il en a lu.
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

# Les actes et les examens se paient à la caisse ; ils ne se remettent jamais au comptoir.
PREFIXES_NON_REMIS = ("ACT-", "EXA-")

Statut = Literal["apayer", "aretirer", "partiel", "retire"]


def se_remet(code: str | None) -> bool:
    """Une ligne se remet au comptoir, sauf un acte ou un examen."""
    return not (code or "").startswith(PREFIXES_NON_REMIS)


def statut(payee: bool, prescrite: int, remise: int) -> Statut:
    """Où en est une ligne : à payer, à retirer, retirée en partie, ou retirée."""
    if not payee:
        return "apayer"
    if remise <= 0:
        return "aretirer"
    if remise < prescrite:
        return "partiel"
    return "retire"


def reste(prescrite: int, remise: int) -> int:
    return max(prescrite - remise, 0)


def allergie_concerne(atc_allergie: str, atc_ligne: str | None) -> bool:
    """Une allergie concerne une ligne quand son code ATC est un préfixe de celui de la ligne :
    une allergie aux AINS, `M01A`, concerne l'ibuprofène, `M01AE01`."""
    return bool(atc_ligne) and bool(atc_allergie) and atc_ligne.upper().startswith(atc_allergie.upper())  # type: ignore[union-attr]


@dataclass(frozen=True)
class AllergieConcernee:
    libelle: str
    lignes: list[str]


def allergies_concernees(
    allergies: Iterable[tuple[str, Sequence[str]]], lignes: Mapping[str, str | None]
) -> list[AllergieConcernee]:
    """Les allergies du patient qui concernent au moins une ligne, chacune avec ces lignes.

    `allergies` : (libellé, codes ATC) ; `lignes` : identifiant de ligne → son code ATC.
    """
    concernees = []
    for libelle, codes in allergies:
        ids = [id_ for id_, atc in lignes.items() if any(allergie_concerne(code, atc) for code in codes)]
        if ids:
            concernees.append(AllergieConcernee(libelle=libelle, lignes=ids))
    return concernees


@dataclass(frozen=True)
class EtatDeLigne:
    payee: bool
    prescrite: int
    remise: int


class DelivranceRefusee(Exception):
    """La délivrance demandée ne peut pas s'écrire. `statut` : le statut HTTP qui le dit."""

    def __init__(self, statut: int, detail: str) -> None:
        super().__init__(detail)
        self.statut = statut
        self.detail = detail


def verifier(
    demande: Sequence[tuple[str, int]],
    etats: Mapping[str, EtatDeLigne],
    lignes_allergiques: set[str],
    allergie_reconnue: bool,
) -> None:
    """Refuse (`DelivranceRefusee`) une délivrance qui ne peut pas s'écrire, sinon ne dit rien.

    `demande` : (identifiant de ligne, quantité) ; `etats` : les lignes remettables de l'ordonnance.
    """
    if not demande:
        raise DelivranceRefusee(422, "aucune ligne à remettre")
    vues: set[str] = set()
    for id_, quantite in demande:
        if id_ in vues:
            raise DelivranceRefusee(422, "une ligne demandée deux fois")
        vues.add(id_)
        etat = etats.get(id_)
        if etat is None:
            raise DelivranceRefusee(404, "ligne inconnue sur cette ordonnance")
        if quantite < 1:
            raise DelivranceRefusee(422, "quantité à remettre nulle ou négative")
        if not etat.payee:
            raise DelivranceRefusee(409, "ligne non payée : elle se paie d'abord à la caisse")
        if quantite > reste(etat.prescrite, etat.remise):
            raise DelivranceRefusee(409, "quantité au-delà de ce qui reste à remettre")
    if not allergie_reconnue and vues & lignes_allergiques:
        raise DelivranceRefusee(409, "allergie du patient à cette ligne : à reconnaître avant de remettre")
