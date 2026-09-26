"""Le jeu de démonstration, lu en objets de `commun.modele`.

Des fichiers TOML écrits à la main dans le vocabulaire de Lafia, à côté de ce module, avec des
identifiants fixes. Tout y est synthétique, sauf les noms des établissements, structures publiques
réelles ; les mots de passe et les codes carnet de démonstration sont publics. Le chargement
(`donnees.chargement`) écrit le jeu dans le noyau ; les mêmes fichiers donnent à identite ses comptes,
de sorte que chaque jeton désigne des personnes et des lieux que le noyau connaît.
"""

import tomllib
from dataclasses import dataclass
from importlib.resources import files
from typing import Any

from commun.jeton import Role
from commun.modele import (
    Adresse,
    Agent,
    Etablissement,
    LieuDeNaissance,
    Niveau,
    Officine,
    Patient,
    PersonneAPrevenir,
    Produit,
    Sexe,
    Tarif,
)


def _lire(fichier: str) -> dict[str, Any]:
    return tomllib.loads((files(__name__) / f"{fichier}.toml").read_text(encoding="utf-8"))


def etablissements() -> list[Etablissement]:
    return [
        Etablissement(
            id=e["id"],
            nom=e["nom"],
            sigle=e["sigle"],
            niveau=Niveau(e["niveau"]),
            departement=e["departement"],
            commune=e["commune"],
        )
        for e in _lire("etablissements")["etablissement"]
    ]


def officines() -> list[Officine]:
    return [
        Officine(id=o["id"], nom=o["nom"], departement=o["departement"], commune=o["commune"])
        for o in _lire("officines")["officine"]
    ]


def _agent(a: dict[str, Any]) -> Agent:
    return Agent(id=a["id"], nom=a["nom"], prenoms=tuple(a["prenoms"]), role=Role(a["role"]))


def agents() -> list[Agent]:
    """Les agents, chacun une fois, quel que soit le nombre de ses comptes."""
    return [_agent(a) for a in _lire("agents")["agent"]]


@dataclass(frozen=True)
class CompteDAgent:
    """Un compte d'agent : de quoi se connecter, l'agent qu'il désigne, l'établissement où il ouvre."""

    identifiant: str
    mot_de_passe: str
    agent: Agent
    etablissement: Etablissement
    reserve_aux_tests: bool
    """Compte que la suite de tests verrouille exprès : jamais listé sur une page de connexion."""


@dataclass(frozen=True)
class CompteDOfficine:
    """Le compte unique d'une officine : ses pharmaciens n'ont pas de compte dans Lafia."""

    identifiant: str
    mot_de_passe: str
    officine: Officine


def comptes() -> list[CompteDAgent | CompteDOfficine]:
    """Les comptes des agents, un par établissement où chacun travaille, puis ceux des officines."""
    etablissements_par_id = {e.id: e for e in etablissements()}
    return [
        *(
            CompteDAgent(
                identifiant=c["identifiant"],
                mot_de_passe=c["mot_de_passe"],
                agent=_agent(a),
                etablissement=etablissements_par_id[c["etablissement"]],
                reserve_aux_tests=c.get("reserve_aux_tests", False),
            )
            for a in _lire("agents")["agent"]
            for c in a["compte"]
        ),
        *(
            CompteDOfficine(
                identifiant=o["compte"]["identifiant"],
                mot_de_passe=o["compte"]["mot_de_passe"],
                officine=officine,
            )
            for o, officine in zip(_lire("officines")["officine"], officines(), strict=True)
        ),
    ]


def _personne_a_prevenir(contact: dict[str, Any] | None) -> PersonneAPrevenir | None:
    if contact is None:
        return None
    return PersonneAPrevenir(
        nom=contact["nom"],
        prenoms=tuple(contact["prenoms"]),
        relation=contact["relation"],
        telephone=contact["telephone"],
    )


def patients() -> list[Patient]:
    return [
        Patient(
            id=p["id"],
            npi=p["npi"],
            nom=p["nom"],
            prenoms=tuple(p["prenoms"]),
            sexe=Sexe(p["sexe"]),
            naissance=p["naissance"],
            lieu_de_naissance=LieuDeNaissance(**p["lieu_de_naissance"]),
            nationalite=p["nationalite"],
            adresse=Adresse(**p["adresse"]),
            langues=tuple(p["langues"]),
            telephone=p.get("telephone"),
            personne_a_prevenir=_personne_a_prevenir(p.get("personne_a_prevenir")),
        )
        for p in _lire("patients")["patient"]
    ]


@dataclass(frozen=True)
class CitoyenDeDemonstration:
    """Le NPI d'un patient du jeu, et le code carnet de son dernier reçu."""

    npi: str
    code_carnet: str
    reserve_aux_tests: bool
    """NPI que la suite de tests verrouille exprès : jamais listé sur une page de connexion."""


def citoyens() -> list[CitoyenDeDemonstration]:
    return [
        CitoyenDeDemonstration(
            npi=c["npi"], code_carnet=c["code_carnet"], reserve_aux_tests=c.get("reserve_aux_tests", False)
        )
        for c in _lire("citoyens")["citoyen"]
    ]


def tarifs() -> list[Tarif]:
    """Le tarif de chaque produit et acte du catalogue dans chaque établissement : le prix que le
    catalogue donne au niveau de l'établissement. Les officines n'en ont pas."""
    catalogue = _lire("catalogue")["produit"]
    return [
        Tarif(
            etablissement=etablissement.id,
            produit=Produit(code=p["code"], libelle=p["libelle"], atc=p.get("atc")),
            prix=p["prix"][etablissement.niveau],
        )
        for etablissement in etablissements()
        for p in catalogue
    ]
