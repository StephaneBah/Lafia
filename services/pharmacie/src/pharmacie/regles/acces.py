"""Qui le service pharmacie sert : le pharmacien d'un établissement, et l'officine.

Le pharmacien ne voit que les lignes payées, les allergies et les traitements au long cours.
L'officine, connectée sous son propre nom, consulte une ordonnance par son numéro et déclare les
lignes qu'elle a vendues ; sa portée vient de son seul rôle, puisqu'elle n'est pas un établissement.
Les soignants, le caissier et le citoyen ont chacun leur service, et rien à faire ici.
"""

from commun.jeton import Role

ROLES_ADMIS = frozenset({Role.PHARMACIEN, Role.OFFICINE})
