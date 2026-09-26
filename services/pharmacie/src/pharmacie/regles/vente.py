"""Ce que l'officine peut vendre d'une ordonnance, et si une vente déclarée peut s'écrire.

Une officine vend les médicaments d'une ordonnance, jamais un acte ni un examen. Une ligne payée à
la caisse d'un établissement se retire à la pharmacie de cet établissement : l'officine ne la vend
pas. Une ligne remise en entier ne se vend plus. Le paiement reste dans le logiciel de l'officine.

Règles pures : `pharmacie.officine` leur donne ce qu'il a lu du noyau.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from pharmacie.regles.delivrance import DelivranceRefusee, EtatDeLigne, reste

PREFIXE_VENDU = "MED-"


def se_vend(code: str | None) -> bool:
    """Une ligne se vend en officine quand c'est un médicament du catalogue."""
    return (code or "").startswith(PREFIXE_VENDU)


@dataclass(frozen=True)
class Vendabilite:
    vendable: bool
    raison: str | None = None


def vendabilite(etat: EtatDeLigne, etablissement: str | None) -> Vendabilite:
    """Si l'officine peut vendre la ligne, et sinon pourquoi. `etablissement` : le nom de
    l'établissement où la ligne se sert."""
    if etat.payee:
        lieu = etablissement or "l'établissement"
        return Vendabilite(False, f"payée à la caisse de {lieu}, à retirer à sa pharmacie")
    if reste(etat.prescrite, etat.remise) <= 0:
        return Vendabilite(False, "déjà remise en entier")
    return Vendabilite(True)


def verifier(demande: Sequence[tuple[str, int]], etats: Mapping[str, EtatDeLigne]) -> None:
    """Refuse (`DelivranceRefusee`) une vente qui ne peut pas s'écrire, sinon ne dit rien.

    `demande` : (identifiant de ligne, quantité) ; `etats` : les lignes vendables ou non de l'ordonnance.
    """
    if not demande:
        raise DelivranceRefusee(422, "aucune ligne vendue")
    vues: set[str] = set()
    for id_, quantite in demande:
        if id_ in vues:
            raise DelivranceRefusee(422, "une ligne déclarée deux fois")
        vues.add(id_)
        etat = etats.get(id_)
        if etat is None:
            raise DelivranceRefusee(404, "ligne inconnue sur cette ordonnance")
        if quantite < 1:
            raise DelivranceRefusee(422, "quantité vendue nulle ou négative")
        if etat.payee:
            raise DelivranceRefusee(409, "ligne payée à la caisse d'un établissement : elle se retire à sa pharmacie")
        if quantite > reste(etat.prescrite, etat.remise):
            raise DelivranceRefusee(409, "quantité au-delà de ce qui reste à remettre")
