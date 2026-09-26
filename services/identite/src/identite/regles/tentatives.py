"""Ce qui empêche de deviner un mot de passe ou un code carnet par essais successifs.

- Cinq échecs sur un même identifiant ou un même NPI le verrouillent 15 minutes, même face aux bons
  identifiants : qui devine n'apprend rien d'un compte verrouillé. Un succès remet son compte à zéro.
- 50 échecs d'une même adresse en 15 minutes la refusent jusqu'à la fin de la fenêtre : une machine ne
  répand pas ses essais sur de nombreux NPI. L'adresse est celle que la passerelle transmet.
- Un essai compte comme un échec dès qu'il commence, pour l'adresse puis pour l'identifiant ou le
  NPI, et n'est rendu que s'il réussit : des essais lancés ensemble ne passent pas entre la lecture
  d'un compteur et son écriture. Un essai refusé par le verrou de son identifiant ou de son NPI est
  rendu à l'adresse, puisque rien n'a été vérifié. Un NPI mal formé n'a pas de compteur : l'essai
  échoue, compté pour la seule adresse.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

ECHECS_AVANT_VERROU = 5
ECHECS_PAR_ADRESSE = 50
FENETRE = timedelta(minutes=15)


@dataclass(frozen=True)
class Cle:
    """Ce que compte un compteur d'échecs : un identifiant, un NPI, ou une adresse."""

    nature: Literal["identifiant", "npi", "adresse"]
    valeur: str

    @property
    def limite(self) -> int:
        """Combien d'échecs la clé admet dans une fenêtre."""
        return ECHECS_PAR_ADRESSE if self.nature == "adresse" else ECHECS_AVANT_VERROU

    def __str__(self) -> str:
        return f"{self.nature}:{self.valeur}"


@dataclass(frozen=True)
class Compteur:
    """Les essais comptés sur une clé depuis le début de sa fenêtre, réussis ou non encore rendus."""

    echecs: int
    depuis: datetime


def apres_un_essai(cle: Cle, compteur: Compteur, maintenant: datetime) -> Compteur:
    """Le compteur de `cle` après un essai de plus. Une fenêtre écoulée repart de zéro ; celle de
    l'essai qui atteint la limite repart de lui, pour que le verrou qui le suit dure une fenêtre entière."""
    if compteur.depuis <= maintenant - FENETRE:
        return Compteur(echecs=1, depuis=maintenant)
    echecs = compteur.echecs + 1
    return Compteur(echecs=echecs, depuis=maintenant if echecs == cle.limite else compteur.depuis)


def verrouillee(cle: Cle, compteur: Compteur) -> bool:
    """Si l'essai qui vient d'être compté dépasse la limite : il est refusé sans rien vérifier."""
    return compteur.echecs > cle.limite
