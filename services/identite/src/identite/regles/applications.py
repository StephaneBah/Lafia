"""Chaque application connecte ses rôles (ADR 0004) : identite ne connecte un rôle que sur une application qui le sert.

Un rôle a son application ; seuls le médecin et l'infirmier en ont une seconde, relecture, où ils valident
les propositions d'une Extraction (F6).

L'application est celle de l'hôte de la requête, `<application>.<domaine>`, que la requête arrive par
l'entrée publique de la passerelle ou par son entrée interne (`:8080`).
"""

from enum import StrEnum

from commun.jeton import Role


class Application(StrEnum):
    """L'application d'un acteur, servie sur son sous-domaine."""

    SOIN = "soin"
    CAISSE = "caisse"
    PHARMACIE = "pharmacie"
    CITOYEN = "citoyen"
    NUMERISATION = "numerisation"
    RELECTURE = "relecture"


ROLES_PAR_APPLICATION: dict[Application, frozenset[Role]] = {
    Application.SOIN: frozenset({Role.MEDECIN, Role.INFIRMIER}),
    Application.CAISSE: frozenset({Role.CAISSIER}),
    Application.PHARMACIE: frozenset({Role.PHARMACIEN, Role.OFFICINE}),
    Application.CITOYEN: frozenset({Role.CITOYEN}),
    Application.NUMERISATION: frozenset({Role.AGENT_DE_NUMERISATION}),
    # La Relecture et le Contrôle par les agents de relecture, la validation par les soignants : une même application (F6).
    Application.RELECTURE: frozenset({Role.AGENT_DE_RELECTURE, Role.MEDECIN, Role.INFIRMIER}),
}


def application_de_l_hote(hote: str, domaine: str) -> Application | None:
    """L'application que désigne l'hôte `soin.<domaine>` ou `soin.<domaine>:8080` ; `None` pour tout autre."""
    nom, _, _ = hote.lower().partition(":")
    application, _, reste = nom.partition(".")
    if reste != domaine:
        return None
    try:
        return Application(application)
    except ValueError:
        return None


def origine(application: Application, domaine: str) -> str:
    """L'origine des pages de l'application : celle que le navigateur envoie avec leurs formulaires."""
    return f"https://{application}.{domaine}"
