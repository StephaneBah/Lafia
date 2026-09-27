"""Ce que le dossier approfondi accepte : une allergie d'une classe du catalogue, un groupe sanguin
parmi huit, un antécédent familial avec son lien, un traitement nommé."""

from commun.fhir.soin import ALLERGIES, GROUPES_SANGUINS


class SaisieRefusee(Exception):
    """Ce qui est saisi sort d'un catalogue ou manque d'un élément : rien n'en est écrit."""


def verifier_allergie(code_atc: str) -> str:
    """Le libellé de la classe ATC ; `SaisieRefusee` hors du catalogue des allergies."""
    if code_atc not in ALLERGIES:
        raise SaisieRefusee(f"classe d'allergie hors du catalogue : {code_atc}")
    return ALLERGIES[code_atc]


def groupe_sanguin(saisie: str) -> str:
    """Le groupe sanguin tel qu'il est écrit (`A−` avec le signe moins), quelle que soit sa saisie."""
    valeur = saisie.strip().upper().replace(" ", "").replace("-", "−").replace("–", "−")
    if valeur not in GROUPES_SANGUINS:
        raise SaisieRefusee("groupe sanguin : A, B, AB ou O, suivi de + ou −")
    return valeur


def verifier_antecedent(type_: str, lien: str | None) -> None:
    """Un antécédent familial dit de quel parent il s'agit ; un antécédent du patient n'en dit rien."""
    if type_ == "familial" and lien is None:
        raise SaisieRefusee("un antécédent familial dit le lien de parenté")
    if type_ != "familial" and lien is not None:
        raise SaisieRefusee("seul un antécédent familial a un lien de parenté")


def libelle_du_traitement(produit: str | None, libelle_du_produit: str | None, libelle: str | None) -> str:
    """Le nom du traitement : celui du catalogue quand le produit y est, le texte saisi sinon."""
    if produit is not None and libelle_du_produit is None:
        raise SaisieRefusee(f"produit sans tarif à cet établissement : {produit}")
    nom = libelle_du_produit or libelle
    if not nom:
        raise SaisieRefusee("un traitement nomme un produit du catalogue ou un libellé")
    return nom
