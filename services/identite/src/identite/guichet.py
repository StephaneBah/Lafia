"""Le guichet d'identite : il ouvre, renouvelle et ferme les sessions, dit qui les tient, et émet les
codes carnet.

Les routes (`identite.service`) n'y ajoutent que HTTP : formulaires, cookies, redirections. Le journal
cite le Practitioner ou l'Organization d'un compte, le `sub` d'un citoyen, et les issues : jamais un
identifiant tapé, un NPI, un nom, un mot de passe ni un code.
"""

import logging
import secrets
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel

from commun.jeton import Agent, Citoyen, Officine, Porteur, Role
from identite.base import BaseDIdentite
from identite.empreintes import empreinte_rapide, hacher, verifier
from identite.jetons import SignataireDeJetons
from identite.regles.applications import ROLES_PAR_APPLICATION, Application
from identite.regles.code_carnet import normaliser, nouveau_code, npi_valide
from identite.regles.sessions import expiration_du_jeton, fin_de_session
from identite.regles.tentatives import Cle, verrouillee

journal = logging.getLogger("identite")


class Refus(StrEnum):
    """Pourquoi une connexion est refusée : la page de connexion en montre le message."""

    IDENTIFIANTS = "identifiants"
    """Identifiant ou mot de passe, NPI ou code : un seul message, qui ne dit pas lequel est faux."""
    APPLICATION = "application"
    """Le compte n'ouvre pas cette application."""
    VERROUILLE = "verrouille"
    """Trop d'échecs sur cet identifiant, ce NPI ou depuis cette adresse."""


@dataclass(frozen=True)
class SessionOuverte:
    """Une session ouverte ou renouvelée : ce que portent ses deux cookies, et pour combien de temps."""

    jeton: str
    duree_du_jeton: timedelta
    identifiant: str
    """Secret du cookie de renouvellement ; la base n'en garde que l'empreinte."""
    duree_restante: timedelta


class SessionAgent(BaseModel):
    """Un agent connecté, tel que son application l'affiche."""

    sub: str
    role: Role
    etablissement: str
    nom: str
    nom_etablissement: str


class SessionOfficine(BaseModel):
    """Une officine connectée, tel que son application l'affiche."""

    sub: str
    role: Literal[Role.OFFICINE] = Role.OFFICINE
    nom: str


class SessionCitoyen(BaseModel):
    """Un citoyen connecté, tel que son application l'affiche : jamais son NPI."""

    sub: str
    role: Literal[Role.CITOYEN] = Role.CITOYEN


def _maintenant() -> datetime:
    return datetime.now(timezone.utc)


class Guichet:
    def __init__(self, base: BaseDIdentite, signataire: SignataireDeJetons) -> None:
        self._base = base
        self._signataire = signataire

    async def connecter(
        self, identifiant: str, mot_de_passe: str, application: Application, adresse: str
    ) -> SessionOuverte | Refus:
        """Connecte un agent ou une officine par son identifiant et son mot de passe."""
        compte = await self._base.compte(identifiant)
        # Un identifiant inconnu peut être un mot de passe tapé au mauvais endroit : il ne s'écrit pas.
        qui = compte.porteur.sub if compte else "compte inconnu"
        refus = await self._essayer(
            adresse,
            Cle("identifiant", identifiant),
            lambda: verifier(compte.empreinte if compte else None, mot_de_passe),
        )
        if refus:
            journal.info("connexion refusée (%s) : %s", refus, qui)
            return refus
        assert compte is not None
        if compte.porteur.role not in ROLES_PAR_APPLICATION[application]:
            journal.info("connexion refusée (application %s) : %s", application, qui)
            return Refus.APPLICATION
        journal.info("connexion de %s sur %s", qui, application)
        return await self._ouvrir(compte.porteur, application)

    async def connecter_citoyen(
        self, npi: str, code: str, application: Application, adresse: str
    ) -> SessionOuverte | Refus:
        """Connecte un citoyen par son NPI et le code carnet de son dernier reçu. Son `sub` est tiré au
        hasard à chaque connexion : jamais tiré de son NPI."""
        if Role.CITOYEN not in ROLES_PAR_APPLICATION[application]:
            journal.info("connexion citoyen refusée (application %s)", application)
            return Refus.APPLICATION

        async def code_concordant() -> bool:
            # Un NPI mal formé n'est cherché nulle part.
            return npi_valide(npi) and await verifier(await self._base.empreinte_du_code(npi), normaliser(code))

        refus = await self._essayer(adresse, Cle("npi", npi) if npi_valide(npi) else None, code_concordant)
        if refus:
            journal.info("connexion citoyen refusée (%s)", refus)
            return refus
        citoyen = Citoyen(sub=secrets.token_urlsafe(16), npi=npi)
        journal.info("connexion du citoyen %s", citoyen.sub)
        return await self._ouvrir(citoyen, application)

    async def renouveler(self, identifiant_de_session: str, application: Application) -> SessionOuverte | None:
        """Un nouveau jeton, si la session est encore ouverte sur cette application ; `None` sinon."""
        maintenant = _maintenant()
        identifiant = empreinte_rapide(identifiant_de_session)
        ouverte = await self._base.session(identifiant, application, maintenant)
        if ouverte is None:
            return None
        porteur, debut = ouverte
        fin = fin_de_session(porteur.role, debut, maintenant)
        await self._base.prolonger_session(identifiant, fin)
        return self._session(porteur, identifiant_de_session, maintenant, fin)

    async def deconnecter(self, identifiant_de_session: str) -> None:
        """Ferme la session : son cookie de renouvellement n'obtient plus de jeton."""
        await self._base.fermer_session(empreinte_rapide(identifiant_de_session))

    async def presenter(self, porteur: Porteur) -> SessionAgent | SessionOfficine | SessionCitoyen | None:
        """Le porteur d'un jeton tel que son application l'affiche : un agent, son nom et celui de son
        établissement ; une officine, son nom ; un citoyen, son seul `sub`. `None` pour un jeton dont
        aucun compte ne répond."""
        if isinstance(porteur, Citoyen):
            return SessionCitoyen(sub=porteur.sub)
        noms = await self._base.noms(porteur)
        if noms is None:
            return None
        if isinstance(porteur, Officine):
            return SessionOfficine(sub=porteur.sub, nom=noms.nom)
        assert noms.nom_etablissement is not None
        return SessionAgent(
            sub=porteur.sub,
            role=porteur.role,
            etablissement=porteur.etablissement,
            nom=noms.nom,
            nom_etablissement=noms.nom_etablissement,
        )

    async def emettre_code(self, npi: str, soignant: Agent) -> str:
        """Un nouveau code carnet pour `npi`, qui remplace le précédent, rendu une seule fois (ADR 0005).
        Il est enregistré avec le soignant et l'établissement qui l'ont demandé."""
        code = nouveau_code()
        await self._base.remplacer_code(npi, await hacher(normaliser(code)), soignant, _maintenant())
        journal.info("code carnet émis à la demande de %s, à %s", soignant.sub, soignant.etablissement)
        return code

    async def _essayer(
        self, adresse: str, cle: Cle | None, essai_reussi: Callable[[], Awaitable[bool]]
    ) -> Refus | None:
        """Un essai de connexion depuis `adresse` sur `cle`, compté comme le veut
        `identite.regles.tentatives` ; `None` quand il réussit. Sans clé, seule l'adresse compte."""
        maintenant = _maintenant()
        depuis_l_adresse = Cle("adresse", adresse)
        if verrouillee(depuis_l_adresse, await self._base.compter_un_essai(depuis_l_adresse, maintenant)):
            return Refus.VERROUILLE
        if cle and verrouillee(cle, await self._base.compter_un_essai(cle, maintenant)):
            await self._base.rendre(depuis_l_adresse)
            return Refus.VERROUILLE
        if not await essai_reussi():
            return Refus.IDENTIFIANTS
        if cle:
            await self._base.remettre_a_zero(cle)
        await self._base.rendre(depuis_l_adresse)
        return None

    async def _ouvrir(self, porteur: Porteur, application: Application) -> SessionOuverte:
        maintenant = _maintenant()
        await self._base.oublier(maintenant)
        identifiant = secrets.token_urlsafe(32)
        fin = fin_de_session(porteur.role, maintenant, maintenant)
        await self._base.ouvrir_session(empreinte_rapide(identifiant), application, porteur, maintenant, fin)
        return self._session(porteur, identifiant, maintenant, fin)

    def _session(self, porteur: Porteur, identifiant: str, maintenant: datetime, fin: datetime) -> SessionOuverte:
        expiration = expiration_du_jeton(maintenant, fin)
        return SessionOuverte(
            jeton=self._signataire.signer(porteur, expiration),
            duree_du_jeton=expiration - maintenant,
            identifiant=identifiant,
            duree_restante=fin - maintenant,
        )
