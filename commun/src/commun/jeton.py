"""Le contrat des jetons de session (ADR 0004), et leur vérification par chaque service, sans appeler identite.

identite signe les jetons de sa clé privée Ed25519 (EdDSA) ; chaque service les vérifie avec la
clé publique lue dans `JETON_CLE_PUBLIQUE`. Un service compromis ne peut donc pas en forger. La
signature reste chez identite : ce module ne tient que ce que les deux côtés partagent, le porteur
et ses revendications (`revendications`, et sa lecture inverse `porteur_des_revendications`), la durée de vie, et la
règle de la clé de développement (`lire_cle`).

Revendications, selon le porteur, plus `exp` pour tous :
- agent : `sub`, l'identifiant de son Practitioner ; `role`, médecin, infirmier, caissier ou
  pharmacien ; `etablissement`, l'identifiant de l'Organization où il s'est connecté ;
- officine : `sub`, l'identifiant de son Organization ; `role`, officine ;
- citoyen : `sub`, tiré au hasard à chaque connexion ; `role`, citoyen ; `npi`.
"""

import base64
import binascii
import logging
import os
import time
from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass, field
from datetime import timedelta
from enum import StrEnum
from typing import Any, Literal, TypeAlias, TypeGuard

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
# identite émet des jetons de 15 minutes ; un service refuse ceux qui expirent plus d'une heure après.
DUREE_DE_VIE = timedelta(minutes=15)
DUREE_DE_VIE_MAXIMALE = timedelta(hours=1)

# Clé publique de la paire de développement, dont la clé privée est publique (identite.jetons,
# tests/conftest.py). Une pile servie sur localhost s'en sert quand JETON_CLE_PUBLIQUE est vide ;
# toute autre la refuse.
CLE_PUBLIQUE_DE_DEVELOPPEMENT = "MCowBQYDK2VwAyEAcn8QgDKMYePA7Hrtw1Kxh8YaI8g7BrT6GsIYQczFpG0="

journal = logging.getLogger("commun.jeton")


class Role(StrEnum):
    MEDECIN = "médecin"
    INFIRMIER = "infirmier"
    CAISSIER = "caissier"
    PHARMACIEN = "pharmacien"
    OFFICINE = "officine"
    CITOYEN = "citoyen"


@dataclass(frozen=True)
class Agent:
    """Un professionnel authentifié, rattaché à un établissement."""

    sub: str
    role: Role
    etablissement: str


@dataclass(frozen=True)
class Officine:
    """Une officine, connectée sous son propre nom. Elle n'est pas un établissement : son jeton n'en
    nomme aucun, et sa portée vient de son seul rôle."""

    sub: str
    role: Literal[Role.OFFICINE] = field(default=Role.OFFICINE, init=False)


@dataclass(frozen=True)
class Citoyen:
    """Un citoyen, qui n'agit que sur son propre NPI."""

    sub: str
    npi: str
    role: Literal[Role.CITOYEN] = field(default=Role.CITOYEN, init=False)


# Qui porte un jeton vérifié.
Porteur: TypeAlias = Agent | Officine | Citoyen


class JetonInvalide(Exception):
    """Jeton mal formé, expiré, signé d'une autre clé, ou aux revendications hors du format commun."""


def _texte(valeur: object) -> TypeGuard[str]:
    return isinstance(valeur, str) and bool(valeur)


def revendications(porteur: Porteur) -> dict[str, str]:
    """Ce qu'un jeton dit de `porteur`, hors expiration : ce que identite signe, et que
    `porteur_des_revendications` relit."""
    match porteur:
        case Agent(etablissement=etablissement):
            return {"sub": porteur.sub, "role": porteur.role, "etablissement": etablissement}
        case Officine():
            return {"sub": porteur.sub, "role": porteur.role}
        case Citoyen(npi=npi):
            return {"sub": porteur.sub, "role": porteur.role, "npi": npi}


def porteur_des_revendications(revendications: Mapping[str, Any]) -> Porteur:
    """Le porteur que disent des revendications, si elles suivent le format commun ; `JetonInvalide`
    sinon. Les services les lisent d'un jeton dont la signature est vérifiée ; identite, de sa base."""
    try:
        role = Role(revendications["role"])
    except ValueError as erreur:
        raise JetonInvalide("rôle inconnu") from erreur
    sub = revendications["sub"]
    etablissement = revendications.get("etablissement")
    npi = revendications.get("npi")
    if _texte(sub):
        if role is Role.CITOYEN:
            if _texte(npi) and etablissement is None:
                return Citoyen(sub=sub, npi=npi)
        elif role is Role.OFFICINE:
            if etablissement is None and npi is None:
                return Officine(sub=sub)
        elif _texte(etablissement) and npi is None:
            return Agent(sub=sub, role=role, etablissement=etablissement)
    raise JetonInvalide(f"revendications non conformes pour le rôle {role}")


def lire_cle(variable: str, cle_de_developpement: str) -> bytes:
    """La clé DER que donne la variable d'environnement `variable` : la ligne base64 entre les bornes
    de son PEM.

    Sur localhost (`LAFIA_DOMAINE`), sans elle, `cle_de_developpement`. Sur tout autre domaine, elle
    est exigée et la clé de développement refusée : une pile déployée n'émet ni n'accepte jamais un
    jeton que chacun peut signer. identite lit ainsi sa clé privée, chaque service sa clé publique.
    """
    local = os.environ.get("LAFIA_DOMAINE") == "localhost"
    valeur = os.environ.get(variable) or (cle_de_developpement if local else None)
    if not valeur:
        raise RuntimeError(f"{variable} manquante : clé Ed25519 des jetons de session.")
    if valeur == cle_de_developpement and not local:
        raise RuntimeError(f"{variable} : la clé de développement ne sert que sur localhost.")
    try:
        return base64.b64decode(valeur, validate=True)
    except binascii.Error as erreur:
        raise RuntimeError(f"{variable} illisible : base64 d'une clé DER.") from erreur


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


def _role_non_admis() -> HTTPException:
    return HTTPException(status.HTTP_403_FORBIDDEN, detail="rôle non admis")


class VerificateurDeJetons:
    def __init__(self, cle_publique: Ed25519PublicKey) -> None:
        self._cle_publique = cle_publique

    @classmethod
    def depuis_environnement(cls) -> "VerificateurDeJetons":
        """Clé publique lue dans `JETON_CLE_PUBLIQUE`, par la règle de `lire_cle`."""
        try:
            cle = load_der_public_key(lire_cle("JETON_CLE_PUBLIQUE", CLE_PUBLIQUE_DE_DEVELOPPEMENT))
        except ValueError as erreur:
            raise RuntimeError("JETON_CLE_PUBLIQUE illisible : clé publique DER.") from erreur
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
        return porteur_des_revendications(revendications)

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

        401 sans jeton valide ; 403 pour une officine, un citoyen ou un agent d'un autre rôle.
        """

        def agent_admis(porteur: Porteur = Depends(self.porteur)) -> Agent:
            if not isinstance(porteur, Agent) or porteur.role not in roles_admis:
                raise _role_non_admis()
            return porteur

        return agent_admis

    def agent_ou_officine(self, roles_admis: Collection[Role]) -> Callable[..., Agent | Officine]:
        """Dépendance FastAPI, garde d'un service qui sert des agents et des officines : l'agent ou
        l'officine du jeton, si son rôle est dans `roles_admis`.

        401 sans jeton valide ; 403 pour un citoyen, ou un porteur d'un autre rôle.
        """

        def agent_ou_officine_admis(porteur: Porteur = Depends(self.porteur)) -> Agent | Officine:
            if not isinstance(porteur, Agent | Officine) or porteur.role not in roles_admis:
                raise _role_non_admis()
            return porteur

        return agent_ou_officine_admis

    def citoyen(self) -> Callable[..., Citoyen]:
        """Dépendance FastAPI, garde du service citoyen : le citoyen du jeton.

        401 sans jeton valide ; 403 pour un agent, quel que soit son rôle, ou une officine.
        """

        def citoyen_admis(porteur: Porteur = Depends(self.porteur)) -> Citoyen:
            if not isinstance(porteur, Citoyen):
                raise _role_non_admis()
            return porteur

        return citoyen_admis
