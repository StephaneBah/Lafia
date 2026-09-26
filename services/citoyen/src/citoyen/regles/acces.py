"""Qui le service citoyen sert, et ce qu'il lui rend : le citoyen, sur son propre NPI.

Les soignants, le caissier et le pharmacien ont chacun leur service, et rien à faire ici : la garde
`citoyen` de `commun.jeton` refuse tout agent. Le NPI du jeton désigne le carnet que le service
ouvre ; il ne quitte jamais le service, pas même vers l'application du citoyen, qui n'en a pas l'usage.
"""

from typing import Literal

from pydantic import BaseModel

from commun.jeton import Citoyen, Role


class SessionCitoyen(BaseModel):
    """Le citoyen connecté, tel que son application le voit : sans son NPI."""

    sub: str
    role: Literal[Role.CITOYEN] = Role.CITOYEN


def session_du_citoyen(citoyen: Citoyen) -> SessionCitoyen:
    """Ce que le service rend du citoyen connecté : son identifiant et son rôle, jamais son NPI."""
    return SessionCitoyen(sub=citoyen.sub)
