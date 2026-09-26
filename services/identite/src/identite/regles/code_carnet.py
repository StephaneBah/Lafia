"""Le code carnet (ADR 0003, 0005), et le NPI qu'il accompagne.

Un code, ce sont 6 caractères de l'alphabet du numéro d'ordonnance, sans 0, O, 1, I ni L, montrés en
deux groupes : `K7M-4PX`. Lisible à voix haute, il se tape sans lecteur ; la saisie se normalise,
tirets et espaces ôtés, en capitales, et c'est le code normalisé que l'on hache. Seuls les soignants
en obtiennent un, pour le reçu du patient qu'ils viennent de voir.
"""

import re
import secrets

from commun.jeton import Role

ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
LONGUEUR = 6
# Treize chiffres. Tout autre NPI est refusé avant toute recherche.
NPI = re.compile(r"[0-9]{13}")

ROLES_QUI_EMETTENT_UN_CODE = frozenset({Role.MEDECIN, Role.INFIRMIER})


def nouveau_code() -> str:
    """Un code tiré au hasard, tel qu'il s'imprime sur le reçu : `K7M-4PX`."""
    caracteres = "".join(secrets.choice(ALPHABET) for _ in range(LONGUEUR))
    return f"{caracteres[:3]}-{caracteres[3:]}"


def normaliser(saisie: str) -> str:
    """Le code tel qu'on le hache, quelle que soit sa saisie : `k7m 4px` et `K7M-4PX` donnent `K7M4PX`."""
    return re.sub(r"[\s-]", "", saisie).upper()


def npi_valide(npi: str) -> bool:
    return NPI.fullmatch(npi) is not None
