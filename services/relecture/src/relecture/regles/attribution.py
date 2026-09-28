"""La semaine d'un agent de relecture : ses Relectures et ses Contrôles, tirés du pool, jamais de son département.

Deux pools. Celui des Relectures : les Documents numérisés (origine `numerisation`) qu'aucune Tâche ne vise
encore, et ceux dont la Tâche de relecture est restée ouverte une semaine passée (à la fin de sa semaine,
une Tâche non faite retourne au pool, son brouillon avec elle) ; les plus anciens papiers passent d'abord
(l'année du Document, puis la date de sa numérisation). Celui des Contrôles : les Transcriptions confirmées
qu'aucun contrôleur ne tient, les plus anciennes d'abord ; jamais à l'agent qui a fait la relecture.

Un agent ne relit ni ne contrôle jamais un Document déposé dans son propre département : le département
d'un Document est celui de l'établissement où il a été numérisé, que dit le Provenance de son Dépôt
(`onBehalfOf`), ou, pour un Document ajouté pendant une visite, l'AuditEvent qui trace son écriture. Un
Document dont le lieu ne se retrouve pas reste assignable.

Le quota borne ce que l'agent tient ouvert : ses Relectures à faire ou en cours de la semaine, et, à
part, ses Contrôles à faire. Une Relecture confirmée ou close libère sa place ; une Relecture renvoyée
par le Contrôle la reprend. Ce qu'il a fait de sa semaine, `suivi` le compte.
"""

import logging
import os
from collections.abc import Awaitable, Callable
from datetime import date

from commun.fhir import relecture, systemes
from commun.fhir.client import ClientFhir, Ressource, TransactionRefusee, ecriture_si_inchangee
from commun.fhir.dossier import id_de
from commun.jeton import Agent

SERVICE = "relecture"
QUOTA_PAR_DEFAUT = 10
"""La démonstration donne dix Tâches par semaine ; la spécification en prévoit 50 en service réel."""

journal = logging.getLogger(SERVICE)


def quota() -> int:
    """Le quota hebdomadaire d'un agent de relecture : `QUOTA_DE_RELECTURE`, ou 10."""
    valeur = os.environ.get("QUOTA_DE_RELECTURE", "")
    return int(valeur) if valeur.isdigit() and int(valeur) > 0 else QUOTA_PAR_DEFAUT


class Departements:
    """Le département de chaque établissement et de chaque Document, lus une fois par requête."""

    def __init__(self, fhir: ClientFhir) -> None:
        self._fhir = fhir
        self._des_etablissements: dict[str, str | None] = {}

    async def de_l_etablissement(self, etablissement: str | None) -> str | None:
        if not etablissement:
            return None
        if etablissement not in self._des_etablissements:
            organisation = await self._fhir.lire("Organization", etablissement)
            adresse = next(iter((organisation or {}).get("address", [])), {})
            self._des_etablissements[etablissement] = adresse.get("state")
        return self._des_etablissements[etablissement]

    async def du_document(self, document: str) -> str | None:
        return await self.de_l_etablissement(await self._lieu_du_depot(document))

    async def _lieu_du_depot(self, document: str) -> str | None:
        cible = f"DocumentReference/{document}"
        for provenance in await self._fhir.chercher("Provenance", {"target": cible}):
            for agent in provenance.get("agent", []):
                lieu = id_de(agent.get("onBehalfOf"))
                if lieu:
                    return lieu
        for trace in await self._fhir.chercher("AuditEvent", {"entity": cible, "action": "C"}):
            observateur = trace.get("source", {}).get("observer", {})
            if observateur.get("reference", "").startswith("Organization/"):
                return id_de(observateur)
        return None


def _cle_d_anciennete(document: Ressource) -> tuple[str, str]:
    annee = document.get("context", {}).get("period", {}).get("start") or "9999"
    return str(annee), str(document.get("date", ""))


async def attribuer(fhir: ClientFhir, agent: Agent, jour: date) -> int:
    """Complète la semaine de l'agent jusqu'à son quota, Contrôles puis Relectures, depuis les pools ;
    rend le nombre de Tâches ajoutées."""
    semaine = relecture.semaine(jour)
    ouvertes = await relecture.taches_ouvertes_de(fhir, agent.sub)
    manque_de_controles = quota() - sum(1 for t in ouvertes if relecture.etape_de(t) == "controle")
    manque_de_relectures = quota() - sum(
        1 for t in ouvertes if relecture.etape_de(t) == "relecture" and relecture.semaine_de(t) == semaine
    )
    if manque_de_controles <= 0 and manque_de_relectures <= 0:
        return 0
    # Les seuls champs qui disent quel Document est suivi, où en est sa Tâche et à qui elle est : ni le
    # brouillon, ni les propositions.
    taches = await fhir.chercher(
        "Task", {"code": f"{systemes.RELECTURE}|", "_elements": "focus,status,code,meta,owner,requester,authoredOn"}
    )
    departements = Departements(fhir)
    le_mien = await departements.de_l_etablissement(agent.etablissement)

    async def du_mien(document: str | None) -> bool:
        return bool(le_mien and document and await departements.du_document(document) == le_mien)

    ecritures: list[dict[str, object]] = []
    controles = sorted(
        (
            t
            for t in taches
            if relecture.etape_de(t) == "controle" and t.get("status") == "ready" and not t.get("owner")
            and relecture.auteur_de(t) != agent.sub
        ),
        key=lambda t: t.get("authoredOn", ""),
    )
    for controle in controles:
        if manque_de_controles <= 0:
            break
        if await du_mien(relecture.document_de(controle)):
            continue
        # Lue en entier : la recherche n'en a rendu que quelques champs.
        entiere = await fhir.lire("Task", controle["id"])
        if entiere:
            ecritures.append(ecriture_si_inchangee(relecture.reassignee(entiere, agent.sub, jour), entiere))
            manque_de_controles -= 1

    if manque_de_relectures > 0:
        ecritures.extend(await _relectures(fhir, agent, jour, taches, manque_de_relectures, du_mien))
    if not ecritures:
        return 0
    try:
        await fhir.transaction(ecritures)
    except TransactionRefusee as erreur:
        # Un autre agent a pris l'une d'elles au même instant : la prochaine lecture complète la semaine.
        journal.warning("attribution à l'agent %s refusée par le noyau : %s", agent.sub, erreur)
        return 0
    journal.info("%d tâches attribuées à l'agent %s pour la semaine %s", len(ecritures), agent.sub, semaine)
    return len(ecritures)


async def _relectures(
    fhir: ClientFhir,
    agent: Agent,
    jour: date,
    taches: list[Ressource],
    manque: int,
    du_mien: Callable[[str | None], Awaitable[bool]],
) -> list[dict[str, object]]:
    """Les Relectures qui complètent la semaine : Documents sans Tâche, ou dont la Relecture est restée
    ouverte une semaine passée ; les plus vieux papiers d'abord."""
    semaine = relecture.semaine(jour)
    suivis = {relecture.document_de(t) for t in taches}
    perimees = {
        relecture.document_de(t): t
        for t in taches
        if relecture.etape_de(t) == "relecture" and relecture.est_ouverte(t) and (relecture.semaine_de(t) or "") < semaine
    }
    documents = await fhir.chercher("DocumentReference", {"_tag": f"{systemes.ORIGINE}|numerisation", "status": "current"})
    ecritures: list[dict[str, object]] = []
    for document in sorted(documents, key=_cle_d_anciennete):
        if len(ecritures) >= manque:
            break
        patient = id_de(document.get("subject"))
        if not patient or (document["id"] in suivis and document["id"] not in perimees):
            continue
        if await du_mien(document["id"]):
            continue
        perimee = perimees.get(document["id"])
        if perimee:
            entiere = await fhir.lire("Task", perimee["id"])
            if entiere:
                ecritures.append(ecriture_si_inchangee(relecture.reassignee(entiere, agent.sub, jour), entiere))
        else:
            ecritures.append(_creer(relecture.tache_de_relecture(document=document["id"], patient=patient, relecteur=agent.sub, jour=jour)))
    return ecritures


def _creer(tache: Ressource) -> dict[str, object]:
    """Créée seulement si aucune Tâche ne vise déjà ce Document : deux agents servis au même instant
    n'en créent pas deux."""
    return {
        "resource": tache,
        "request": {"method": "POST", "url": "Task", "ifNoneExist": f"focus={tache['focus']['reference']}"},
    }
