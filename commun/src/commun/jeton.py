"""Vérification des jetons de session. Chaque service vérifie seul, sans appeler identite.

identite signe les jetons de sa clé privée Ed25519 (EdDSA) ; chaque service les vérifie avec la
clé publique lue dans `JETON_CLE_PUBLIQUE`. Un service compromis ne peut donc pas en forger.

Revendications, que identite émet :
- `sub` : identifiant de l'agent, ou du citoyen ;
- `role` : médecin, infirmier, caissier, pharmacien ou citoyen ;
- `etablissement` : identifiant de l'Organization de l'agent ; absent pour le citoyen ;
- `npi` : pour le citoyen seulement ;
- `exp` : expiration, quelques minutes après l'émission, jamais plus d'une heure.
"""

import base64
import binascii
import logging
import os
import time
from collections.abc import Callable, Collection
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from typing import Any, TypeAlias, TypeGuard

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import load_der_public_key
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyCookie, HTTPAuthorizationCredentials, HTTPBearer

# Cookie de session de chaque application. Le préfixe `__Host-` oblige le navigateur à le garder
# Secure, sans Domain, sur tout le chemin : il n'est renvoyé qu'au sous-domaine qui l'a posé.
COOKIE_DE_SESSION = "__Host-session"
ALGORITHME = "EdDSA"
REVENDICATIONS_EXIGEES = ["sub", "role", "exp"]
DUREE_DE_VIE_MAXIMALE = timedelta(hours=1)

# Clé publique de la paire de développement, dont la clé privée est publique (tests/conftest.py).
# Une pile servie sur localhost s'en sert quand JETON_CLE_PUBLIQUE est vide ; toute autre la refuse.
CLE_PUBLIQUE_DE_DEVELOPPEMENT = "MCowBQYDK2VwAyEAcn8QgDKMYePA7Hrtw1Kxh8YaI8g7BrT6GsIYQczFpG0="

journal = logging.getLogger("commun.jeton")


class Role(StrEnum):
    MEDECIN = "médecin"
    INFIRMIER = "infirmier"
    CAISSIER = "caissier"
    PHARMACIEN = "pharmacien"
    CITOYEN = "citoyen"


@dataclass(frozen=True)
class Agent:
    """Un professionnel authentifié, rattaché à un établissement."""

    sub: str
    role: Role
    etablissement: str


@dataclass(frozen=True)
class Citoyen:
    """Un citoyen, qui n'agit que sur son propre NPI."""

    sub: str
    npi: str


# Qui porte un jeton vérifié.
Porteur: TypeAlias = Agent | Citoyen


class JetonInvalide(Exception):
    """Jeton mal formé, expiré, signé d'une autre clé, ou aux revendications hors du format commun."""


def _texte(valeur: object) -> TypeGuard[str]:
    return isinstance(valeur, str) and bool(valeur)


def _porteur(revendications: dict[str, Any]) -> Porteur:
    """Le porteur d'un jeton dont la signature est vérifiée, si ses revendications suivent le format commun."""
    try:
        role = Role(revendications["role"])
    except ValueError as erreur:
        raise JetonInvalide("rôle inconnu") from erreur
    sub = revendications["sub"]
    etablissement = revendications.get("etablissement")
    npi = revendications.get("npi")
    if _texte(sub):
        if role is Role.CITOYEN and _texte(npi) and etablissement is None:
            return Citoyen(sub=sub, npi=npi)
        if role is not Role.CITOYEN and _texte(etablissement) and npi is None:
            return Agent(sub=sub, role=role, etablissement=etablissement)
    raise JetonInvalide(f"revendications non conformes pour le rôle {role}")


# Le jeton arrive par le cookie de session de l'application, que la passerelle transmet, ou par
# l'en-tête Authorization, pour les tests et les intégrateurs. Les deux figurent au contrat OpenAPI.
_schema_porteur = HTTPBearer(
    auto_error=False, description="Jeton de session, pour les tests et les intégrateurs."
)
_schema_cookie = APIKeyCookie(
    name=COOKIE_DE_SESSION,
    auto_error=False,
    description="Cookie de session de l'application, transmis par la passerelle.",
)


def _refus(detail: str) -> HTTPException:
    return HTTPException(
        status.HTTP_401_UNAUTHORIZED, detail=detail, headers={"WWW-Authenticate": "Bearer"}
    )


class VerificateurDeJetons:
    def __init__(self, cle_publique: Ed25519PublicKey) -> None:
        self._cle_publique = cle_publique

    @classmethod
    def depuis_environnement(cls) -> "VerificateurDeJetons":
        """Clé publique lue dans `JETON_CLE_PUBLIQUE` : la ligne base64 entre les bornes de son PEM.

        Sur localhost (`LAFIA_DOMAINE`), sans elle, la clé de développement. Sur tout autre domaine,
        elle est exigée et la clé de développement refusée : une pile déployée n'accepte jamais un
        jeton que chacun peut signer.
        """
        local = os.environ.get("LAFIA_DOMAINE") == "localhost"
        valeur = os.environ.get("JETON_CLE_PUBLIQUE") or (
            CLE_PUBLIQUE_DE_DEVELOPPEMENT if local else None
        )
        if not valeur:
            raise RuntimeError("JETON_CLE_PUBLIQUE manquante : clé publique Ed25519 d'identite.")
        if valeur == CLE_PUBLIQUE_DE_DEVELOPPEMENT and not local:
            raise RuntimeError("JETON_CLE_PUBLIQUE : la clé de développement ne sert que sur localhost.")
        try:
            cle = load_der_public_key(base64.b64decode(valeur, validate=True))
        except (binascii.Error, ValueError) as erreur:
            raise RuntimeError("JETON_CLE_PUBLIQUE illisible : base64 d'une clé publique DER.") from erreur
        if not isinstance(cle, Ed25519PublicKey):
            raise RuntimeError("JETON_CLE_PUBLIQUE n'est pas une clé publique Ed25519.")
        return cls(cle)

    def verifier(self, jeton: str) -> Porteur:
        """Vérifie signature, expiration, durée de vie et revendications ; `JetonInvalide` sinon."""
        try:
            revendications = jwt.decode(
                jeton,
                self._cle_publique,
                algorithms=[ALGORITHME],
                options={"require": REVENDICATIONS_EXIGEES},
            )
        except jwt.PyJWTError as erreur:
            # Le nom de l'erreur seulement : son message peut citer le contenu du jeton.
            raise JetonInvalide(type(erreur).__name__) from erreur
        if revendications["exp"] > time.time() + DUREE_DE_VIE_MAXIMALE.total_seconds():
            raise JetonInvalide("expiration au-delà de la durée de vie maximale")
        return _porteur(revendications)

    def porteur(
        self,
        authorization: HTTPAuthorizationCredentials | None = Security(_schema_porteur),
        cookie: str | None = Security(_schema_cookie),
    ) -> Porteur:
        """Dépendance FastAPI : le porteur vérifié du jeton de la requête. 401 sans jeton valide."""
        jeton = authorization.credentials if authorization else cookie
        if not jeton:
            raise _refus("jeton absent")
        try:
            return self.verifier(jeton)
        except JetonInvalide as erreur:
            journal.info("jeton refusé : %s", erreur)
            raise _refus("jeton invalide") from erreur

    def agent(self, roles_admis: Collection[Role]) -> Callable[..., Agent]:
        """Dépendance FastAPI, garde de rôle : l'agent du jeton, si son rôle est admis.

        401 sans jeton valide ; 403 pour un citoyen ou un agent d'un autre rôle.
        """

        def agent_admis(porteur: Porteur = Depends(self.porteur)) -> Agent:
            if not isinstance(porteur, Agent) or porteur.role not in roles_admis:
                raise HTTPException(status.HTTP_403_FORBIDDEN, detail="rôle non admis")
            return porteur

        return agent_admis
