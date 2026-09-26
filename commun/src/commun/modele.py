"""Les choses que Lafia nomme, dans son vocabulaire (CONTEXT.md), sans rien de FHIR.

Le jeu de démonstration les écrit ; `commun.fhir.ressources` les traduit en ressources du noyau.
"""

from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from commun.jeton import Role


class Niveau(StrEnum):
    """Le niveau d'un établissement dans la pyramide sanitaire. Le prix de ses tarifs en dépend."""

    CHU_NATIONAL = "chu-national"
    CHU_DEPARTEMENTAL = "chu-departemental"
    CHU_DE_ZONE = "chu-de-zone"
    CENTRE_DE_SANTE = "centre-de-sante"


@dataclass(frozen=True)
class Etablissement:
    """Une structure de santé où les visites ont lieu."""

    id: str
    nom: str
    sigle: str
    niveau: Niveau
    departement: str
    commune: str


@dataclass(frozen=True)
class Officine:
    """Une pharmacie de ville indépendante, rattachée à aucun établissement."""

    id: str
    nom: str
    departement: str
    commune: str


@dataclass(frozen=True)
class Professionnel:
    """Un agent en tant que personne : soignant, caissier ou pharmacien, quel que soit l'établissement
    où il se connecte. `id` est celui de son Practitioner, et le `sub` de ses jetons."""

    id: str
    nom: str
    prenoms: tuple[str, ...]
    role: Role


class Sexe(StrEnum):
    FEMININ = "féminin"
    MASCULIN = "masculin"


@dataclass(frozen=True)
class LieuDeNaissance:
    commune: str
    pays: str
    """Code ISO 3166 à deux lettres : `BJ`."""


@dataclass(frozen=True)
class Adresse:
    """Où vit un patient, au Bénin, jusqu'au quartier ou au village."""

    departement: str
    commune: str
    arrondissement: str
    quartier: str


@dataclass(frozen=True)
class PersonneAPrevenir:
    nom: str
    prenoms: tuple[str, ...]
    relation: str
    """Ce qu'elle est pour le patient, en toutes lettres : épouse, fils, mère, …"""
    telephone: str


@dataclass(frozen=True)
class Patient:
    """Un citoyen tel que le soin le connaît, identifié par son NPI."""

    id: str
    npi: str
    nom: str
    prenoms: tuple[str, ...]
    sexe: Sexe
    naissance: date
    lieu_de_naissance: LieuDeNaissance
    nationalite: str
    """Code ISO 3166 à deux lettres : `BJ`."""
    adresse: Adresse
    langues: tuple[str, ...]
    """Langues parlées, en codes BCP 47 (`fr`, `fon`, `yo`, …), la plus usuelle d'abord."""
    telephone: str | None = None
    personne_a_prevenir: PersonneAPrevenir | None = None


@dataclass(frozen=True)
class Produit:
    """Un produit ou un acte qu'une ligne d'ordonnance peut porter."""

    code: str
    """Son code dans le catalogue de Lafia : `MED-PARACETAMOL-500`."""
    libelle: str
    atc: str | None = None
    """Pour un médicament, son code dans la classification ATC de l'OMS."""


@dataclass(frozen=True)
class Tarif:
    """Le prix d'un produit ou d'un acte dans un établissement, que la caisse lit sans rien saisir."""

    etablissement: str
    """L'identifiant de l'établissement."""
    produit: Produit
    prix: int
    """En FCFA."""
