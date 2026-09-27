"""Le Dépôt au guichet : l'ouvrir sur un NPI et une pièce d'identité, y numériser des Documents, le clore.

Un Dépôt ne tient aucun état dans le service : son ouverture est un AuditEvent étiqueté de son
identifiant (`commun.fhir.documents.ouverture_du_depot`), ses Documents portent la même étiquette, sa
clôture écrit le Provenance. Seul l'agent qui l'a ouvert s'en sert, et seulement jusqu'à sa clôture.
L'agent ne voit du patient que son nom, ses prénoms et son année de naissance ; il ne saisit aucune
valeur clinique. Chaque lecture et chaque écriture laisse un AuditEvent, au motif `numerisation`.
"""

import logging
import secrets
from datetime import date

from pydantic import BaseModel

from commun.fhir import documents, dossier
from commun.fhir.client import ClientFhir
from commun.fhir.documents import OuvertureDeDepot, Page
from commun.jeton import Agent

SERVICE = "numerisation"
MOTIF = "numerisation"
PREMIERE_ANNEE = 1900

# Les premiers octets de chaque format admis : une page se reconnaît à son contenu, pas à ce qu'elle déclare.
SIGNATURES = {
    "image/jpeg": b"\xff\xd8\xff",
    "image/png": b"\x89PNG\r\n\x1a\n",
    "application/pdf": b"%PDF-",
}

journal = logging.getLogger(SERVICE)


class PatientIntrouvable(Exception):
    """Aucun Patient sous ce NPI."""


class DepotIntrouvable(Exception):
    """Aucun Dépôt ouvert sous cet identifiant."""


class DepotDUnAutreAgent(Exception):
    """Le Dépôt a été ouvert par un autre agent."""


class DepotClos(Exception):
    """Le Dépôt est clos : on n'y ajoute plus rien, on n'y lit plus rien."""


class DocumentIntrouvable(Exception):
    """Aucun Document de ce Dépôt sous cet identifiant, ou aucune page à ce rang."""


class DocumentRefuse(Exception):
    """Type, année, lisibilité ou format d'une page hors de ce que le Document admet."""


class DocumentTropLourd(Exception):
    """Plus de pages, ou une page plus lourde, que l'ADR 0008 n'en admet."""


class IdentiteAuGuichet(BaseModel):
    """Ce que l'agent voit du patient pour le comparer à la pièce d'identité : rien d'autre."""

    nom: str
    prenoms: str
    annee_de_naissance: str | None


class DepotOuvert(BaseModel):
    depot_id: str
    patient: IdentiteAuGuichet


class DocumentDuDepot(BaseModel):
    id: str
    type: str
    annee: str | None
    pages: int


class Depot(BaseModel):
    patient: IdentiteAuGuichet
    documents: list[DocumentDuDepot]


class DocumentAjoute(BaseModel):
    document_id: str
    pages: int


class Cloture(BaseModel):
    depot_id: str
    documents: int


async def _tracer(
    fhir: ClientFhir,
    agent: Agent,
    patient: str,
    action: dossier.Action,
    *,
    ressource: dict[str, str] | None = None,
    etiquettes: list[dict[str, str]] | None = None,
    raison: str | None = None,
) -> None:
    await dossier.tracer(
        fhir,
        patient=patient,
        qui=dossier.reference("Practitioner", agent.sub),
        service=SERVICE,
        action=action,
        motif=MOTIF,
        etablissement=agent.etablissement,
        ressource=ressource,
        etiquettes=etiquettes,
        raison=raison,
    )


async def _identite(fhir: ClientFhir, patient: str) -> IdentiteAuGuichet:
    ressource = await fhir.lire("Patient", patient)
    nom, prenoms, annee = documents.identite_au_guichet(ressource or {})
    return IdentiteAuGuichet(nom=nom, prenoms=prenoms, annee_de_naissance=annee)


async def ouvrir(fhir: ClientFhir, agent: Agent, npi: str, piece: str, reprise: bool) -> DepotOuvert:
    """Ouvre un Dépôt pour le patient du NPI, sa pièce d'identité vérifiée : trace l'ouverture, rend son identité."""
    patient = await dossier.patient_par_npi(fhir, npi)
    if not patient:
        raise PatientIntrouvable()
    depot = secrets.token_hex(16)
    etiquettes = [documents.etiquette_de_depot(depot)]
    if reprise:
        etiquettes.append(documents.etiquette_d_origine("reprise"))
    await _tracer(fhir, agent, patient["id"], "create", etiquettes=etiquettes, raison=piece)
    journal.info("dépôt %s ouvert : patient %s, agent %s", depot, patient["id"], agent.sub)
    return DepotOuvert(depot_id=depot, patient=await _identite(fhir, patient["id"]))


async def _depot_ouvert(fhir: ClientFhir, agent: Agent, depot: str) -> OuvertureDeDepot:
    """Le Dépôt `depot`, s'il est de cet agent et pas encore clos."""
    ouverture = await documents.ouverture_du_depot(fhir, depot)
    if not ouverture:
        raise DepotIntrouvable()
    if ouverture.agent != agent.sub:
        journal.warning("dépôt %s refusé à l'agent %s : ouvert par un autre agent", depot, agent.sub)
        raise DepotDUnAutreAgent()
    if ouverture.clos:
        raise DepotClos()
    return ouverture


def _verifier(type_: str, annee: str, lisibilite: str, pages: list[Page]) -> None:
    if type_ not in documents.TYPES_DE_DOCUMENT or lisibilite not in documents.LISIBILITES:
        raise DocumentRefuse("type ou lisibilité inconnus")
    if not (annee.isdigit() and len(annee) == 4 and PREMIERE_ANNEE <= int(annee) <= date.today().year):
        raise DocumentRefuse("année sur quatre chiffres, passée")
    if not pages:
        raise DocumentRefuse("au moins une page")
    if len(pages) > documents.PAGES_PAR_DOCUMENT:
        raise DocumentTropLourd(f"au plus {documents.PAGES_PAR_DOCUMENT} pages")
    for page in pages:
        signature = SIGNATURES.get(page.format)
        if not signature or not page.octets.startswith(signature):
            raise DocumentRefuse("format accepté : JPEG, PNG ou PDF")
        if len(page.octets) > documents.OCTETS_PAR_PAGE:
            raise DocumentTropLourd("une page ne dépasse pas 3 Mo")


async def ajouter_document(
    fhir: ClientFhir,
    agent: Agent,
    depot: str,
    *,
    type_: str,
    annee: str,
    etablissement_d_origine: str | None,
    lisibilite: str,
    pages: list[Page],
) -> DocumentAjoute:
    """Numérise un Document dans le Dépôt : ses pages en Binary, lui en DocumentReference étiqueté du Dépôt."""
    ouverture = await _depot_ouvert(fhir, agent, depot)
    _verifier(type_, annee, lisibilite, pages)
    ecrit = await documents.ecrire_document(
        fhir,
        patient=ouverture.patient,
        auteur=agent.sub,
        type_=type_,
        annee=annee,
        pages=pages,
        lisibilite=lisibilite,
        etablissement_d_origine=(etablissement_d_origine or "").strip() or None,
        depot=depot,
    )
    await _tracer(fhir, agent, ouverture.patient, "create", ressource=dossier.reference("DocumentReference", ecrit["id"]))
    journal.info("document %s numérisé : %d pages, dépôt %s, agent %s", ecrit["id"], len(pages), depot, agent.sub)
    return DocumentAjoute(document_id=ecrit["id"], pages=len(pages))


async def lire_depot(fhir: ClientFhir, agent: Agent, depot: str) -> Depot:
    """Le Dépôt en cours : l'identité du patient au guichet, et les seuls Documents de ce Dépôt."""
    ouverture = await _depot_ouvert(fhir, agent, depot)
    vus = [documents.document_vu(d) for d in await documents.documents_du_depot(fhir, depot)]
    await _tracer(fhir, agent, ouverture.patient, "read")
    return Depot(
        patient=await _identite(fhir, ouverture.patient),
        documents=[DocumentDuDepot(id=v.id, type=v.type, annee=v.annee, pages=v.pages) for v in vus],
    )


async def lire_page(fhir: ClientFhir, agent: Agent, depot: str, document: str, rang: int) -> Page:
    """La page `rang` d'un Document de ce Dépôt, pour que l'agent la revoie avant de clore."""
    ouverture = await _depot_ouvert(fhir, agent, depot)
    trouve = next((d for d in await documents.documents_du_depot(fhir, depot) if d["id"] == document), None)
    lue = await documents.page(fhir, trouve, rang) if trouve else None
    if not lue:
        raise DocumentIntrouvable()
    await _tracer(fhir, agent, ouverture.patient, "read", ressource=dossier.reference("DocumentReference", document))
    return lue


async def clore(fhir: ClientFhir, agent: Agent, depot: str) -> Cloture:
    """Clôt le Dépôt : le Provenance qui l'enregistre, quand il a des Documents, puis la trace de sa clôture."""
    ouverture = await _depot_ouvert(fhir, agent, depot)
    ids = [d["id"] for d in await documents.documents_du_depot(fhir, depot)]
    if ids:
        await fhir.creer(
            documents.provenance_de_depot(
                depot=depot,
                documents=ids,
                agent=agent.sub,
                etablissement=agent.etablissement,
                piece=ouverture.piece,
                reprise=ouverture.reprise,
            )
        )
    # La trace de clôture porte l'étiquette du Dépôt : un Dépôt vide, qui n'écrit pas de Provenance, est clos aussi.
    await _tracer(fhir, agent, ouverture.patient, "update", etiquettes=[documents.etiquette_de_depot(depot)])
    journal.info("dépôt %s clos : %d documents, agent %s", depot, len(ids), agent.sub)
    return Cloture(depot_id=depot, documents=len(ids))
