"""Qui le service numerisation sert : l'agent de numérisation.

Il ajoute des Documents au dossier et ne lit rien d'autre : du patient, il ne voit que le nom, les
prénoms et l'année de naissance, de quoi les comparer à la pièce d'identité qu'on lui tend. Les
soignants lisent les Documents par soin, le citoyen par citoyen.
"""

from commun.jeton import Role

ROLES_ADMIS = frozenset({Role.AGENT_DE_NUMERISATION})
