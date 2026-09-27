"""Ce qu'une visite peut porter : mesures du catalogue, diagnostic de la courte liste, lignes
d'ordonnance tarifées à l'établissement. Un infirmier ne pose qu'un diagnostic provisoire ; seul un
médecin clôt un cas."""

from commun.fhir.soin import DIAGNOSTICS, MESURES, RESULTATS_TDR
from commun.jeton import Role


class VisiteRefusee(Exception):
    """Ce que la visite porte sort d'un catalogue : rien n'en est écrit."""


def diagnostic_confirme(role: Role, confirme_demande: bool) -> bool:
    """Un diagnostic d'infirmier reste provisoire, quoi qu'il demande."""
    return confirme_demande and role is Role.MEDECIN


def peut_clore(role: Role) -> bool:
    return role is Role.MEDECIN


def verifier_mesure(code: str, valeur: float | str, valeur2: float | None) -> None:
    mesure = MESURES.get(code)
    if mesure is None:
        raise VisiteRefusee(f"mesure hors du catalogue : {code}")
    if mesure.forme == "tdr":
        if valeur not in RESULTATS_TDR:
            raise VisiteRefusee("un TDR est positif ou négatif")
        return
    if not isinstance(valeur, int | float):
        raise VisiteRefusee(f"mesure {code} : valeur numérique attendue")
    if mesure.forme == "tension" and not isinstance(valeur2, int | float):
        raise VisiteRefusee("une tension a deux valeurs : systolique et diastolique")


def verifier_diagnostic(code: str) -> None:
    if code not in DIAGNOSTICS:
        raise VisiteRefusee(f"diagnostic hors de la liste : {code}")


def verifier_ligne(produit: str, tarifs: dict[str, object], moments: list[str], jours: int, quantite: int) -> None:
    if produit not in tarifs:
        raise VisiteRefusee(f"produit sans tarif à cet établissement : {produit}")
    # Un médicament se prend à des moments ; un acte ou un examen (ACT-, EXA-) n'en a pas.
    if produit.startswith("MED-") and not moments:
        raise VisiteRefusee("un médicament a au moins un moment de prise")
    if jours < 1 or quantite < 1:
        raise VisiteRefusee("jours et quantité sont au moins 1")
