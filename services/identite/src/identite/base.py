"""La base d'identite, sa propre PostgreSQL (`base-identite`), que seul identite joint.

Elle tient les comptes, les codes carnet, les sessions et les compteurs d'échecs : aucune donnée
médicale, et aucun secret en clair (`identite.empreintes`). identite crée son schéma au démarrage.
"""

import os
from dataclasses import dataclass
from datetime import datetime

import asyncpg

from commun.jeton import Agent, Officine, Porteur, porteur_des_revendications, revendications
from identite.empreintes import empreinte_rapide
from identite.regles.applications import Application
from identite.regles.tentatives import FENETRE, Cle, Compteur, apres_un_essai

SCHEMA = """
CREATE TABLE IF NOT EXISTS compte (
    identifiant       text PRIMARY KEY,
    mot_de_passe      text NOT NULL,     -- empreinte argon2id
    role              text NOT NULL,
    sub               text NOT NULL,     -- Practitioner de l'agent, ou Organization de l'officine
    etablissement     text,              -- Organization de l'établissement de l'agent ; aucune pour une officine
    nom               text NOT NULL,     -- de l'agent ou de l'officine, tel que les applications l'affichent
    nom_etablissement text
);
CREATE TABLE IF NOT EXISTS code_carnet (
    npi           text PRIMARY KEY,      -- un seul code valable par NPI (ADR 0005)
    code          text NOT NULL,         -- empreinte argon2id du code normalisé
    demande_par   text,                  -- Practitioner du soignant ; aucun pour un code du jeu de démonstration
    etablissement text,
    emis_le       timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS session (
    identifiant   bytea PRIMARY KEY,     -- empreinte SHA-256 de l'identifiant du cookie de renouvellement
    application   text NOT NULL,
    role          text NOT NULL,
    sub           text NOT NULL,
    etablissement text,
    npi           text,
    debut         timestamptz NOT NULL,
    fin           timestamptz NOT NULL
);
CREATE TABLE IF NOT EXISTS tentative (
    cle    bytea PRIMARY KEY,            -- empreinte SHA-256 de la clé : `identifiant:…`, `npi:…` ou `adresse:…`
    echecs integer NOT NULL,             -- essais comptés dans la fenêtre, réussis ou non encore rendus
    depuis timestamptz NOT NULL          -- début de la fenêtre
);
"""


@dataclass(frozen=True)
class Compte:
    """Un compte d'agent ou d'officine : l'empreinte de son mot de passe, et qui il connecte."""

    empreinte: str
    porteur: Agent | Officine


@dataclass(frozen=True)
class Noms:
    """Ce que les applications affichent d'un agent ou d'une officine connectés."""

    nom: str
    nom_etablissement: str | None


def _colonnes(porteur: Porteur) -> tuple[str, str, str | None, str | None]:
    """Le porteur en colonnes, telles que son jeton le dit : rôle, sub, établissement, NPI."""
    dit = revendications(porteur)
    return dit["role"], dit["sub"], dit.get("etablissement"), dit.get("npi")


class BaseDIdentite:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    @classmethod
    async def ouvrir(cls) -> "BaseDIdentite":
        """La base jointe à `BASE_URL`, avec le mot de passe `BASE_MOT_DE_PASSE`, son schéma créé."""
        url = os.environ.get("BASE_URL")
        if not url:
            raise RuntimeError("BASE_URL manquante : adresse de la base d'identite.")
        pool = await asyncpg.create_pool(url, password=os.environ.get("BASE_MOT_DE_PASSE"), min_size=1, max_size=4)
        await pool.execute(SCHEMA)
        return cls(pool)

    async def fermer(self) -> None:
        await self._pool.close()

    # Comptes

    async def enregistrer_compte(
        self, identifiant: str, empreinte: str, porteur: Agent | Officine, noms: Noms
    ) -> None:
        """Crée le compte, ou le remplace s'il existe sous cet identifiant."""
        role, sub, etablissement, _ = _colonnes(porteur)
        await self._pool.execute(
            """
            INSERT INTO compte (identifiant, mot_de_passe, role, sub, etablissement, nom, nom_etablissement)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (identifiant) DO UPDATE SET
                mot_de_passe = EXCLUDED.mot_de_passe, role = EXCLUDED.role, sub = EXCLUDED.sub,
                etablissement = EXCLUDED.etablissement, nom = EXCLUDED.nom,
                nom_etablissement = EXCLUDED.nom_etablissement
            """,
            identifiant, empreinte, role, sub, etablissement, noms.nom, noms.nom_etablissement,
        )

    async def compte(self, identifiant: str) -> Compte | None:
        ligne = await self._pool.fetchrow(
            "SELECT mot_de_passe, role, sub, etablissement FROM compte WHERE identifiant = $1", identifiant
        )
        if ligne is None:
            return None
        porteur = porteur_des_revendications(dict(ligne.items()))
        assert isinstance(porteur, Agent | Officine)
        return Compte(empreinte=ligne["mot_de_passe"], porteur=porteur)

    async def noms(self, porteur: Agent | Officine) -> Noms | None:
        """Les noms d'un agent connecté dans un établissement, ou d'une officine."""
        role, sub, etablissement, _ = _colonnes(porteur)
        ligne = await self._pool.fetchrow(
            "SELECT nom, nom_etablissement FROM compte"
            " WHERE role = $1 AND sub = $2 AND etablissement IS NOT DISTINCT FROM $3 LIMIT 1",
            role, sub, etablissement,
        )
        return Noms(nom=ligne["nom"], nom_etablissement=ligne["nom_etablissement"]) if ligne else None

    # Codes carnet

    async def enregistrer_code_de_demonstration(self, npi: str, empreinte: str, maintenant: datetime) -> None:
        """Le code du jeu de démonstration, pour un NPI qui n'en a pas : jamais par-dessus un code émis."""
        await self._pool.execute(
            "INSERT INTO code_carnet (npi, code, emis_le) VALUES ($1, $2, $3) ON CONFLICT (npi) DO NOTHING",
            npi, empreinte, maintenant,
        )

    async def remplacer_code(self, npi: str, empreinte: str, soignant: Agent, maintenant: datetime) -> None:
        """Le nouveau code de `npi`, demandé par `soignant` : il remplace le précédent."""
        await self._pool.execute(
            """
            INSERT INTO code_carnet (npi, code, demande_par, etablissement, emis_le) VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (npi) DO UPDATE SET
                code = EXCLUDED.code, demande_par = EXCLUDED.demande_par,
                etablissement = EXCLUDED.etablissement, emis_le = EXCLUDED.emis_le
            """,
            npi, empreinte, soignant.sub, soignant.etablissement, maintenant,
        )

    async def empreinte_du_code(self, npi: str) -> str | None:
        empreinte: str | None = await self._pool.fetchval("SELECT code FROM code_carnet WHERE npi = $1", npi)
        return empreinte

    # Sessions

    async def ouvrir_session(
        self, identifiant: bytes, application: Application, porteur: Porteur, debut: datetime, fin: datetime
    ) -> None:
        await self._pool.execute(
            "INSERT INTO session (identifiant, application, role, sub, etablissement, npi, debut, fin)"
            " VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
            identifiant, application, *_colonnes(porteur), debut, fin,
        )

    async def session(
        self, identifiant: bytes, application: Application, maintenant: datetime
    ) -> tuple[Porteur, datetime] | None:
        """Le porteur et le début de la session, si elle est ouverte sur cette application et pas finie."""
        ligne = await self._pool.fetchrow(
            "SELECT role, sub, etablissement, npi, debut FROM session"
            " WHERE identifiant = $1 AND application = $2 AND fin > $3",
            identifiant, application, maintenant,
        )
        return (porteur_des_revendications(dict(ligne.items())), ligne["debut"]) if ligne else None

    async def prolonger_session(self, identifiant: bytes, fin: datetime) -> None:
        await self._pool.execute("UPDATE session SET fin = $2 WHERE identifiant = $1", identifiant, fin)

    async def fermer_session(self, identifiant: bytes) -> None:
        await self._pool.execute("DELETE FROM session WHERE identifiant = $1", identifiant)

    # Compteurs d'échecs

    async def compter_un_essai(self, cle: Cle, maintenant: datetime) -> Compteur:
        """Compte un essai de plus sur `cle`, selon `identite.regles.tentatives`, et rend son compteur.
        La ligne reste verrouillée le temps du calcul : des essais simultanés sont comptés un à un."""
        empreinte = empreinte_rapide(str(cle))
        async with self._pool.acquire() as connexion, connexion.transaction():
            await connexion.execute(
                "INSERT INTO tentative (cle, echecs, depuis) VALUES ($1, 0, $2) ON CONFLICT (cle) DO NOTHING",
                empreinte, maintenant,
            )
            ligne = await connexion.fetchrow("SELECT echecs, depuis FROM tentative WHERE cle = $1 FOR UPDATE", empreinte)
            assert ligne is not None, "la ligne vient d'être créée"
            compteur = apres_un_essai(cle, Compteur(echecs=ligne["echecs"], depuis=ligne["depuis"]), maintenant)
            await connexion.execute(
                "UPDATE tentative SET echecs = $2, depuis = $3 WHERE cle = $1", empreinte, compteur.echecs, compteur.depuis
            )
        return compteur

    async def remettre_a_zero(self, cle: Cle) -> None:
        await self._pool.execute("DELETE FROM tentative WHERE cle = $1", empreinte_rapide(str(cle)))

    async def rendre(self, cle: Cle) -> None:
        """Décompte un essai qui n'était pas un échec."""
        await self._pool.execute(
            "UPDATE tentative SET echecs = echecs - 1 WHERE cle = $1 AND echecs > 0", empreinte_rapide(str(cle))
        )

    async def oublier(self, maintenant: datetime) -> None:
        """Efface les sessions finies et les compteurs dont la fenêtre est écoulée."""
        await self._pool.execute("DELETE FROM session WHERE fin <= $1", maintenant)
        await self._pool.execute("DELETE FROM tentative WHERE depuis <= $1", maintenant - FENETRE)
