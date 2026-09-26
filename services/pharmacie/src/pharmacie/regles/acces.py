"""Qui le service pharmacie sert : le pharmacien.

Il ne voit que les lignes payées, les allergies et les traitements au long cours ; les soignants,
le caissier et le citoyen ont chacun leur service, et rien à faire ici.
"""

from commun.jeton import Role

ROLES_ADMIS = frozenset({Role.PHARMACIEN})
