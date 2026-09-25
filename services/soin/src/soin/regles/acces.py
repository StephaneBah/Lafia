"""Qui le service soin sert : les soignants, médecin et infirmier.

Le caissier, le pharmacien et le citoyen ont chacun leur service, et rien à faire ici.
"""

from commun.jeton import Role

ROLES_ADMIS = frozenset({Role.MEDECIN, Role.INFIRMIER})
