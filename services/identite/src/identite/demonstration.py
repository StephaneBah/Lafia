"""Le jeu de démonstration, côté identite : ses comptes et ses codes carnet, chargés à chaque démarrage,
et les comptes que la page de connexion de chaque application liste.

Les mêmes fichiers (`donnees`) écrivent le noyau : chaque jeton désigne un Practitioner et une
Organization qu'il tient. Un compte est créé, ou mis à jour, par son identifiant ; un compte absent
des fichiers est laissé tel quel. Un code carnet du jeu n'est écrit que pour un NPI qui n'en a pas,
jamais par-dessus un code émis depuis. Mots de passe et codes du jeu sont publics : tout y est
synthétique. Les comptes et les NPI réservés aux tests ne sont jamais listés.
"""

from datetime import datetime, timezone
from functools import cache
from typing import Literal

from pydantic import BaseModel

import donnees
from commun.jeton import Agent, Officine, Role
from identite.base import BaseDIdentite, Noms
from identite.empreintes import hacher
from identite.regles.applications import ROLES_PAR_APPLICATION, Application
from identite.regles.code_carnet import normaliser


class CompteDeDemonstration(BaseModel):
    """Un compte d'agent ou d'officine, tel que la page de connexion le montre."""

    identifiant: str
    mot_de_passe: str
    role: Role
    structure: str
    """Le nom de l'établissement de l'agent, ou celui de l'officine."""


class CitoyenDeDemonstration(BaseModel):
    """Un citoyen de démonstration, tel que la page de connexion du citoyen le montre."""

    npi: str
    code: str
    role: Literal[Role.CITOYEN] = Role.CITOYEN


def _porteur_et_noms(compte: donnees.CompteDAgent | donnees.CompteDOfficine) -> tuple[Agent | Officine, Noms]:
    match compte:
        case donnees.CompteDAgent(agent=agent, etablissement=etablissement):
            return (
                Agent(sub=agent.id, role=agent.role, etablissement=etablissement.id),
                Noms(nom=" ".join((*agent.prenoms, agent.nom)), nom_etablissement=etablissement.nom),
            )
        case donnees.CompteDOfficine(officine=officine):
            return Officine(sub=officine.id), Noms(nom=officine.nom, nom_etablissement=None)


async def charger(base: BaseDIdentite) -> None:
    """Écrit dans la base les comptes et les codes carnet du jeu de démonstration."""
    for compte in donnees.comptes():
        porteur, noms = _porteur_et_noms(compte)
        await base.enregistrer_compte(compte.identifiant, await hacher(compte.mot_de_passe), porteur, noms)
    maintenant = datetime.now(timezone.utc)
    for citoyen in donnees.citoyens():
        empreinte = await hacher(normaliser(citoyen.code_carnet))
        await base.enregistrer_code_de_demonstration(citoyen.npi, empreinte, maintenant)


@cache
def comptes_de_demonstration(application: Application) -> list[CompteDeDemonstration | CitoyenDeDemonstration]:
    """Les comptes de démonstration des rôles que `application` connecte, sans ceux réservés aux tests."""
    roles = ROLES_PAR_APPLICATION[application]
    comptes: list[CompteDeDemonstration | CitoyenDeDemonstration] = []
    for compte in donnees.comptes():
        porteur, noms = _porteur_et_noms(compte)
        reserve = isinstance(compte, donnees.CompteDAgent) and compte.reserve_aux_tests
        if porteur.role in roles and not reserve:
            comptes.append(
                CompteDeDemonstration(
                    identifiant=compte.identifiant,
                    mot_de_passe=compte.mot_de_passe,
                    role=porteur.role,
                    structure=noms.nom_etablissement or noms.nom,
                )
            )
    if Role.CITOYEN in roles:
        comptes += [
            CitoyenDeDemonstration(npi=citoyen.npi, code=citoyen.code_carnet)
            for citoyen in donnees.citoyens()
            if not citoyen.reserve_aux_tests
        ]
    return comptes
