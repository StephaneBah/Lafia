"""Les Documents du dossier et leur origine (ADR 0007, 0008 ; docs/specs/F5-reprise-du-passe-medical.md).

Une page est un `Binary` du noyau ; un Document, un `DocumentReference` qui liste ses pages ; un Dépôt,
un `Provenance` écrit à sa clôture ; le report d'une entrée depuis un Document, un `Provenance` aussi.
Chaque entrée porte son origine en `meta.tag`. numerisation, soin et citoyen lisent et écrivent par ici :
une seule forme, un seul lecteur.
"""

import base64
from dataclasses import dataclass
from typing import Literal

from commun.fhir import systemes
from commun.fhir.client import ClientFhir, Ressource
from commun.fhir.dossier import id_de, maintenant, reference

Origine = Literal["visite", "numerisation", "declaration", "report", "extraction"]

TYPES_DE_DOCUMENT = {
    "carnet": "Carnet de santé",
    "compte-rendu": "Compte rendu",
    "resultat-analyse": "Résultat d'analyse",
    "ordonnance": "Ancienne ordonnance",
    "imagerie": "Imagerie",
    "certificat": "Certificat",
    "autre": "Autre document",
}
LISIBILITES = {"lisible": "Lisible", "partiel": "Partiellement lisible"}
PIECES_D_IDENTITE = {
    "cni": "Carte nationale d'identité",
    "passeport": "Passeport",
    "acte-de-naissance": "Acte de naissance",
    "carte-lafia": "Carte biométrique",
    "autre": "Autre pièce",
}

# ADR 0008 : ce qu'une page et un Document admettent.
FORMATS = {"image/jpeg", "image/png", "application/pdf"}
OCTETS_PAR_PAGE = 3 * 1024 * 1024
PAGES_PAR_DOCUMENT = 20


def etiquette_d_origine(origine: Origine | Literal["reprise"]) -> dict[str, str]:
    return {"system": systemes.ORIGINE, "code": origine}


def etiquette_de_depot(depot: str) -> dict[str, str]:
    return {"system": systemes.DEPOT, "code": depot}


def avec_origine(ressource: Ressource, origine: Origine) -> Ressource:
    """`ressource`, marquée de son origine (ADR 0007). À appeler sur toute entrée écrite au dossier."""
    meta = ressource.setdefault("meta", {})
    etiquettes = [e for e in meta.get("tag", []) if e.get("system") != systemes.ORIGINE]
    meta["tag"] = [*etiquettes, etiquette_d_origine(origine)]
    return ressource


def origine_de(ressource: Ressource) -> str | None:
    """L'origine d'une entrée, ou None pour une entrée écrite avant F5."""
    return next(
        (e.get("code") for e in ressource.get("meta", {}).get("tag", []) if e.get("system") == systemes.ORIGINE),
        None,
    )


@dataclass(frozen=True)
class Page:
    """Une page reçue : son format et ses octets."""

    format: str
    octets: bytes


class PageRefusee(ValueError):
    """Une page hors des formats ou des limites de l'ADR 0008."""


def verifier_pages(pages: list[Page]) -> None:
    if not pages or len(pages) > PAGES_PAR_DOCUMENT:
        raise PageRefusee(f"entre 1 et {PAGES_PAR_DOCUMENT} pages")
    for page in pages:
        if page.format not in FORMATS:
            raise PageRefusee("format accepté : JPEG, PNG ou PDF")
        if len(page.octets) > OCTETS_PAR_PAGE:
            raise PageRefusee("une page ne dépasse pas 3 Mo")


def binary(page: Page, patient: str) -> Ressource:
    return {
        "resourceType": "Binary",
        "contentType": page.format,
        "securityContext": reference("Patient", patient),
        "data": base64.b64encode(page.octets).decode(),
    }


def document_reference(
    *,
    patient: str,
    auteur: str,
    type_: str,
    annee: str,
    pages: list[tuple[str, Page]],
    lisibilite: str,
    etablissement_d_origine: str | None,
    depot: str | None,
) -> Ressource:
    """Un Document numérisé : `pages` sont les (identifiant du Binary, page) déjà écrits, dans l'ordre."""
    ressource: Ressource = {
        "resourceType": "DocumentReference",
        "status": "current",
        "docStatus": "final",
        "type": {
            "coding": [{"system": systemes.TYPE_DE_DOCUMENT, "code": type_, "display": TYPES_DE_DOCUMENT[type_]}],
            "text": TYPES_DE_DOCUMENT[type_],
        },
        "category": [
            {"coding": [{"system": systemes.ORIGINE, "code": "numerisation", "display": "Numérisé"}], "text": "Numérisé"}
        ],
        "subject": reference("Patient", patient),
        "date": maintenant(),
        "author": [reference("Practitioner", auteur)],
        "context": {"period": {"start": annee}, "sourcePatientInfo": reference("Patient", patient)},
        "content": [
            {
                "attachment": {
                    "contentType": page.format,
                    "url": f"Binary/{id_}",
                    "size": len(page.octets),
                    "title": f"Page {rang}",
                }
            }
            for rang, (id_, page) in enumerate(pages, start=1)
        ],
        "extension": [{"url": systemes.LISIBILITE, "valueCode": lisibilite}],
    }
    if etablissement_d_origine:
        ressource["description"] = etablissement_d_origine
    avec_origine(ressource, "numerisation")
    if depot:
        ressource["meta"]["tag"].append(etiquette_de_depot(depot))
    return ressource


async def ecrire_document(
    fhir: ClientFhir,
    *,
    patient: str,
    auteur: str,
    type_: str,
    annee: str,
    pages: list[Page],
    lisibilite: str,
    etablissement_d_origine: str | None = None,
    depot: str | None = None,
) -> Ressource:
    """Écrit les pages puis le Document qui les liste ; rend le DocumentReference écrit."""
    verifier_pages(pages)
    if type_ not in TYPES_DE_DOCUMENT or lisibilite not in LISIBILITES:
        raise PageRefusee("type ou lisibilité inconnus")
    ecrites = [(await fhir.creer(binary(page, patient)))["id"] for page in pages]
    return await fhir.creer(
        document_reference(
            patient=patient,
            auteur=auteur,
            type_=type_,
            annee=annee,
            pages=list(zip(ecrites, pages)),
            lisibilite=lisibilite,
            etablissement_d_origine=etablissement_d_origine,
            depot=depot,
        )
    )


@dataclass(frozen=True)
class DocumentVu:
    """Un Document tel que les applications le montrent."""

    id: str
    patient: str | None
    type: str
    libelle_du_type: str
    annee: str | None
    etablissement: str | None
    lisibilite: str | None
    pages: int
    origine: str | None
    depose_le: str | None
    auteur: str | None


def document_vu(ressource: Ressource) -> DocumentVu:
    codage = next(iter(ressource.get("type", {}).get("coding", [])), {})
    lisibilite = next(
        (e.get("valueCode") for e in ressource.get("extension", []) if e.get("url") == systemes.LISIBILITE), None
    )
    return DocumentVu(
        id=ressource["id"],
        patient=id_de(ressource.get("subject")),
        type=codage.get("code", "autre"),
        libelle_du_type=codage.get("display") or ressource.get("type", {}).get("text", "Document"),
        annee=ressource.get("context", {}).get("period", {}).get("start"),
        etablissement=ressource.get("description"),
        lisibilite=lisibilite,
        pages=len(ressource.get("content", [])),
        origine=origine_de(ressource),
        depose_le=ressource.get("date"),
        auteur=id_de(next(iter(ressource.get("author", [])), None)),
    )


def formats_des_pages(ressource: Ressource) -> list[str]:
    """Le format de chaque page d'un Document, dans l'ordre : de quoi montrer une image ou ouvrir un PDF."""
    return [c.get("attachment", {}).get("contentType", "") for c in ressource.get("content", [])]


async def documents_du_patient(fhir: ClientFhir, patient: str) -> list[Ressource]:
    """Les Documents courants du patient, du plus récent au plus ancien."""
    trouves = await fhir.chercher("DocumentReference", {"subject": f"Patient/{patient}", "status": "current"})
    return sorted(trouves, key=lambda d: d.get("date", ""), reverse=True)


async def documents_du_depot(fhir: ClientFhir, depot: str) -> list[Ressource]:
    return await fhir.chercher("DocumentReference", {"_tag": f"{systemes.DEPOT}|{depot}"})


async def page(fhir: ClientFhir, document: Ressource, rang: int) -> Page | None:
    """La page `rang` (à partir de 1) d'un Document, lue dans le noyau."""
    contenus = document.get("content", [])
    if not 1 <= rang <= len(contenus):
        return None
    piece = contenus[rang - 1]["attachment"]
    lue = await fhir.lire("Binary", piece["url"].rsplit("/", 1)[-1])
    if not lue:
        return None
    return Page(format=lue.get("contentType", piece.get("contentType", "")), octets=base64.b64decode(lue.get("data", "")))


def provenance_de_depot(*, depot: str, documents: list[str], agent: str, etablissement: str, piece: str, reprise: bool) -> Ressource:
    """Le Dépôt clos : ses Documents, qui les a numérisés, où, et la pièce d'identité vérifiée."""
    etiquettes = [etiquette_de_depot(depot)] + ([etiquette_d_origine("reprise")] if reprise else [])
    return {
        "resourceType": "Provenance",
        "meta": {"tag": etiquettes},
        "target": [reference("DocumentReference", id_) for id_ in documents],
        "recorded": maintenant(),
        "activity": {"coding": [{"system": systemes.ORIGINE, "code": "numerisation", "display": "Numérisation"}]},
        "agent": [{"who": reference("Practitioner", agent), "onBehalfOf": reference("Organization", etablissement)}],
        "reason": [{"text": f"Identité vérifiée : {PIECES_D_IDENTITE.get(piece, piece)}"}],
    }


def provenance_de_report(*, cible: dict[str, str], document: str, soignant: str) -> Ressource:
    """Une entrée reportée par un soignant depuis un Document (origine `report`)."""
    return {
        "resourceType": "Provenance",
        "target": [cible],
        "recorded": maintenant(),
        "activity": {"coding": [{"system": systemes.ORIGINE, "code": "report", "display": "Report depuis un document"}]},
        "agent": [{"who": reference("Practitioner", soignant)}],
        "entity": [{"role": "source", "what": reference("DocumentReference", document)}],
    }


# Un Dépôt ouvert n'est rien d'autre que l'AuditEvent de son ouverture (action `C`), étiqueté `DEPOT` :
# il dit le patient, l'agent qui l'a ouvert, son établissement, la pièce d'identité vérifiée (le texte
# du motif) et la Reprise (étiquette d'origine `reprise`). La clôture laisse un AuditEvent de mise à
# jour (action `U`) au même `DEPOT`, et le Provenance du Dépôt quand il a des Documents.


@dataclass(frozen=True)
class OuvertureDeDepot:
    """Ce que l'ouverture d'un Dépôt a tracé, et s'il est clos depuis."""

    depot: str
    patient: str
    agent: str
    etablissement: str | None
    piece: str
    reprise: bool
    clos: bool


def _porte_l_etiquette(ressource: Ressource, etiquette: dict[str, str]) -> bool:
    return any(
        e.get("system") == etiquette["system"] and e.get("code") == etiquette["code"]
        for e in ressource.get("meta", {}).get("tag", [])
    )


def _id_si(ref: dict[str, str] | None, type_: str) -> str | None:
    return id_de(ref) if ref and ref.get("reference", "").startswith(f"{type_}/") else None


async def ouverture_du_depot(fhir: ClientFhir, depot: str) -> OuvertureDeDepot | None:
    """L'ouverture du Dépôt `depot`, lue dans ses AuditEvent, et s'il est clos ; None pour un Dépôt inconnu."""
    traces = await fhir.chercher("AuditEvent", {"_tag": f"{systemes.DEPOT}|{depot}"})
    ouverture = next((t for t in traces if t.get("action") == "C"), None)
    if not ouverture:
        return None
    agent = next(iter(ouverture.get("agent", [])), {})
    usage = next(iter(agent.get("purposeOfUse", [])), {})
    patient = next(
        (p for p in (_id_si(e.get("what"), "Patient") for e in ouverture.get("entity", [])) if p), None
    )
    clos = any(t.get("action") == "U" for t in traces) or bool(
        await fhir.chercher("Provenance", {"_tag": f"{systemes.DEPOT}|{depot}"})
    )
    return OuvertureDeDepot(
        depot=depot,
        patient=patient or "",
        agent=_id_si(agent.get("who"), "Practitioner") or "",
        etablissement=_id_si(ouverture.get("source", {}).get("observer"), "Organization"),
        piece=str(usage.get("text", "")),
        reprise=_porte_l_etiquette(ouverture, etiquette_d_origine("reprise")),
        clos=clos,
    )


def identite_au_guichet(patient: Ressource) -> tuple[str, str, str | None]:
    """Nom, prénoms et année de naissance d'un Patient : tout ce que le guichet de numérisation en voit."""
    nom = next(iter(patient.get("name", [])), {})
    naissance = patient.get("birthDate")
    return str(nom.get("family", "")), " ".join(nom.get("given", [])), str(naissance)[:4] if naissance else None
