"""La semaine d'un agent de relecture : son quota de Tâches, tirées du pool, jamais de son département.

Le pool, ce sont les Documents numérisés (origine `numerisation`) qu'aucune Tâche de relecture ne vise
encore, et ceux dont la Tâche de triage est restée ouverte une semaine passée : à la fin de sa semaine,
une Tâche non faite retourne au pool. Les plus anciens papiers passent d'abord (l'année du Document, puis
la date de sa numérisation).

Un agent ne relit jamais un Document déposé dans son propre département : le département d'un Document
est celui de l'établissement où il a été numérisé, que dit le Provenance de son Dépôt (`onBehalfOf`),
ou, pour un Document ajouté pendant une visite, l'AuditEvent qui trace son écriture. Un Document dont
le lieu ne se retrouve pas reste assignable.

Le quota compte les Tâches que l'agent tient pour la semaine : celles à trier, et celles qu'il a closes
au triage. Une Tâche qu'il a passée en validation n'est plus à lui, et libère sa place.
"""

import logging
import os
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
    """Complète la semaine de l'agent jusqu'à son quota, depuis le pool ; rend le nombre de Tâches ajoutées."""
    semaine = relecture.semaine(jour)
    manque = quota() - len(await relecture.taches_de(fhir, agent.sub, semaine))
    if manque <= 0:
        return 0
    # Les seuls champs qui disent quel Document est suivi, et où en est sa Tâche : pas les propositions.
    taches = await fhir.chercher("Task", {"code": f"{systemes.RELECTURE}|", "_elements": "focus,status,code,meta"})
    suivis = {relecture.document_de(t) for t in taches}
    # Une Tâche de triage non faite d'une semaine passée retourne au pool.
    perimees = {
        relecture.document_de(t): t
        for t in taches
        if relecture.etape_de(t) == "triage"
        and t.get("status") == "ready"
        and (relecture.semaine_de(t) or "") < semaine
    }
    documents = await fhir.chercher(
        "DocumentReference", {"_tag": f"{systemes.ORIGINE}|numerisation", "status": "current"}
    )
    departements = Departements(fhir)
    le_mien = await departements.de_l_etablissement(agent.etablissement)
    ecritures: list[dict[str, object]] = []
    for document in sorted(documents, key=_cle_d_anciennete):
        if len(ecritures) >= manque:
            break
        patient = id_de(document.get("subject"))
        if not patient or (document["id"] in suivis and document["id"] not in perimees):
            continue
        if le_mien and await departements.du_document(document["id"]) == le_mien:
            continue
        perimee = perimees.get(document["id"])
        if perimee:
            # Lue en entier : la recherche n'en a rendu que quelques champs.
            entiere = await fhir.lire("Task", perimee["id"])
            if entiere:
                ecritures.append(_reassigner(entiere, agent.sub, jour))
        else:
            ecritures.append(_creer(relecture.tache_de_relecture(document=document["id"], patient=patient, relecteur=agent.sub, jour=jour)))
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


def _creer(tache: Ressource) -> dict[str, object]:
    """Créée seulement si aucune Tâche ne vise déjà ce Document : deux agents servis au même instant
    n'en créent pas deux."""
    return {
        "resource": tache,
        "request": {"method": "POST", "url": "Task", "ifNoneExist": f"focus={tache['focus']['reference']}"},
    }


def _reassigner(tache: Ressource, relecteur: str, jour: date) -> dict[str, object]:
    return ecriture_si_inchangee(relecture.reassignee(tache, relecteur, jour), tache)
