"""Qui le service caisse sert : le caissier.

Il ne voit que les ordonnances et leurs montants ; les soignants, le pharmacien et le citoyen ont
chacun leur service, et rien à faire ici.
"""

from commun.jeton import Role

ROLES_ADMIS = frozenset({Role.CAISSIER})
