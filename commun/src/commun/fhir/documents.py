"""Les Documents du dossier et leur origine (ADR 0007, 0008 ; docs/specs/F5-reprise-du-passe-medical.md).

Une page est un `Binary` du noyau ; un Document, un `DocumentReference` qui liste ses pages ; un Dépôt,
un `Provenance` écrit à sa clôture ; le report d'une entrée depuis un Document, un `Provenance` aussi.
Chaque entrée porte son origine en `meta.tag`. numerisation, soin et citoyen lisent et écrivent par ici :
une seule forme, un seul lecteur.
"""

import base64
from dataclasses import dataclass
from datetime import date
from typing import Literal, get_args

from pydantic import BaseModel

from commun.fhir import systemes
from commun.fhir.client import ClientFhir, Ressource
from commun.fhir.dossier import id_de, maintenant, reference

Origine = Literal["visite", "numerisation", "declaration", "report", "extraction"]

TypeDeDocument = Literal["carnet", "compte-rendu", "resultat-analyse", "ordonnance", "imagerie", "certificat", "autre"]
Lisibilite = Literal["lisible", "partiel"]
PieceDIdentite = Literal["cni", "passeport", "acte-de-naissance", "carte-lafia", "autre"]

TYPES_DE_DOCUMENT: dict[str, str] = {
    "carnet": "Carnet de santé",
    "compte-rendu": "Compte rendu",
    "resultat-analyse": "Résultat d'analyse",
    "ordonnance": "Ancienne ordonnance",
    "imagerie": "Imagerie",
    "certificat": "Certificat",
    "autre": "Autre document",
}
LISIBILITES: dict[str, str] = {"lisible": "Lisible", "partiel": "Partiellement lisible"}
PIECES_D_IDENTITE: dict[str, str] = {
    "cni": "Carte nationale d'identité",
    "passeport": "Passeport",
    "acte-de-naissance": "Acte de naissance",
    "carte-lafia": "Carte biométrique",
    "autre": "Autre pièce",
}

assert set(get_args(TypeDeDocument)) == set(TYPES_DE_DOCUMENT)
assert set(get_args(Lisibilite)) == set(LISIBILITES)
assert set(get_args(PieceDIdentite)) == set(PIECES_D_IDENTITE)

# ADR 0008 : ce qu'une page et un Document admettent. Une page se reconnaît à ses premiers octets,
# jamais au format qu'elle déclare.
SIGNATURES = {
    "image/jpeg": b"\xff\xd8\xff",
    "image/png": b"\x89PNG",
    "application/pdf": b"%PDF",
}
OCTETS_PAR_PAGE = 3 * 1024 * 1024
PAGES_PAR_DOCUMENT = 20
PREMIERE_ANNEE = 1900
# F6.5 : la note d'un papier abîmé en lui-même, seule manière de garder une page que la capture refuse.
NOTE_DE_PAPIER_ABIME_MAX = 300


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
    """Une page reçue : le format qu'elle déclare, et ses octets."""

    format: str
    octets: bytes


class DocumentRefuse(ValueError):
    """Type, année, lisibilité ou format d'une page hors de ce que le Document admet (422)."""


class DocumentTropLourd(DocumentRefuse):
    """Plus de pages, ou une page plus lourde, que l'ADR 0008 n'en admet (413)."""


def format_reconnu(octets: bytes) -> str | None:
    """Le format d'une page, lu à ses premiers octets : JPEG, PNG ou PDF ; None pour tout autre contenu."""
    return next((format_ for format_, signature in SIGNATURES.items() if octets.startswith(signature)), None)


def valider_document(
    *, type_: str, annee: str, lisibilite: str, pages: list[Page], papier_abime: str | None = None
) -> None:
    """La seule validation d'un Document téléversé, par numerisation comme par soin (ADR 0008).

    `DocumentTropLourd` (413) au-delà de 20 pages ou d'une page de 3 Mo ; `DocumentRefuse` (422) pour
    un type ou une lisibilité inconnus, une année qui n'est pas passée sur quatre chiffres, aucune page,
    une page dont le contenu n'est ni JPEG, ni PNG, ni PDF, ou n'est pas le format qu'elle déclare, ou une
    note de papier abîmé de plus de 300 caractères.
    """
    if papier_abime is not None and len(papier_abime) > NOTE_DE_PAPIER_ABIME_MAX:
        raise DocumentRefuse(f"la note de papier abîmé tient en {NOTE_DE_PAPIER_ABIME_MAX} caractères")
    if type_ not in TYPES_DE_DOCUMENT or lisibilite not in LISIBILITES:
        raise DocumentRefuse("type ou lisibilité inconnus")
    if not (len(annee) == 4 and annee.isascii() and annee.isdigit() and PREMIERE_ANNEE <= int(annee) <= date.today().year):
        raise DocumentRefuse(f"année sur quatre chiffres, de {PREMIERE_ANNEE} à cette année")
    if not pages:
        raise DocumentRefuse("au moins une page")
    if len(pages) > PAGES_PAR_DOCUMENT:
        raise DocumentTropLourd(f"au plus {PAGES_PAR_DOCUMENT} pages")
    for page in pages:
        if len(page.octets) > OCTETS_PAR_PAGE:
            raise DocumentTropLourd("une page ne dépasse pas 3 Mo")
        reconnu = format_reconnu(page.octets)
        if reconnu is None or reconnu != page.format:
            raise DocumentRefuse("format accepté : JPEG, PNG ou PDF, tel que la page le déclare")


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
    papier_abime: str | None = None,
) -> Ressource:
    """Un Document numérisé : `pages` sont les (identifiant du Binary, page) déjà écrits, dans l'ordre.
    `papier_abime` : la note de l'agent quand le papier, abîmé en lui-même, a passé outre la capture."""
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
    if papier_abime:
        ressource["extension"].append({"url": systemes.PAPIER_ABIME, "valueString": papier_abime})
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
    papier_abime: str | None = None,
) -> Ressource:
    """Valide le Document (`valider_document`), écrit ses pages puis le Document qui les liste ; rend le
    DocumentReference écrit. Rien n'est écrit d'un Document refusé. `papier_abime`, vide ou blanc, ne s'écrit pas."""
    papier_abime = (papier_abime or "").strip() or None
    valider_document(type_=type_, annee=annee, lisibilite=lisibilite, pages=pages, papier_abime=papier_abime)
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
            papier_abime=papier_abime,
        )
    )


class DocumentVu(BaseModel):
    """Un Document tel que les services le rendent aux applications : numerisation, soin et citoyen."""

    id: str
    type: str
    """carnet, compte-rendu, resultat-analyse, ordonnance, imagerie, certificat, autre."""
    libelle: str
    annee: str | None
    etablissement: str | None
    """L'établissement d'origine, tel qu'il est écrit sur le papier."""
    lisibilite: str | None
    """lisible ou partiel."""
    pages: int
    formats: list[str]
    """Le format de chaque page, dans l'ordre : une image se montre, un PDF s'ouvre."""
    origine: str | None
    depose_le: str | None
    papier_abime: str | None = None
    """La note de l'agent quand le papier, abîmé en lui-même, a passé outre un contrôle de la capture."""


def formats_des_pages(ressource: Ressource) -> list[str]:
    """Le format de chaque page d'un Document, dans l'ordre : de quoi montrer une image ou ouvrir un PDF."""
    return [c.get("attachment", {}).get("contentType", "") for c in ressource.get("content", [])]


def document_vu(ressource: Ressource) -> DocumentVu:
    codage = next(iter(ressource.get("type", {}).get("coding", [])), {})
    extensions = ressource.get("extension", [])
    lisibilite = next((e.get("valueCode") for e in extensions if e.get("url") == systemes.LISIBILITE), None)
    papier_abime = next((e.get("valueString") for e in extensions if e.get("url") == systemes.PAPIER_ABIME), None)
    return DocumentVu(
        id=ressource["id"],
        type=codage.get("code", "autre"),
        libelle=codage.get("display") or ressource.get("type", {}).get("text", "Document"),
        annee=ressource.get("context", {}).get("period", {}).get("start"),
        etablissement=ressource.get("description"),
        lisibilite=lisibilite,
        pages=len(ressource.get("content", [])),
        formats=formats_des_pages(ressource),
        origine=origine_de(ressource),
        depose_le=ressource.get("date"),
        papier_abime=papier_abime,
    )


async def documents_du_patient(fhir: ClientFhir, patient: str) -> list[Ressource]:
    """Les Documents courants du patient, du plus récent au plus ancien. Une lecture tirée d'un Document
    (origine `extraction` : une Transcription, ADR 0010) n'en est pas un : elle se lit avec son scan."""
    trouves = await fhir.chercher("DocumentReference", {"subject": f"Patient/{patient}", "status": "current"})
    documents = [d for d in trouves if origine_de(d) != "extraction"]
    return sorted(documents, key=lambda d: d.get("date", ""), reverse=True)


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
    """Le Dépôt clos : ses Documents, qui les a numérisés, où, et la pièce d'identité vérifiée.
    Il porte l'origine `numerisation`, et `reprise` quand il est de la Reprise (ADR 0007)."""
    etiquettes = [etiquette_de_depot(depot), etiquette_d_origine("numerisation")]
    if reprise:
        etiquettes.append(etiquette_d_origine("reprise"))
    libelle = PIECES_D_IDENTITE.get(piece, piece)
    return {
        "resourceType": "Provenance",
        "meta": {"tag": etiquettes},
        "target": [reference("DocumentReference", id_) for id_ in documents],
        "recorded": maintenant(),
        "activity": {"coding": [{"system": systemes.ORIGINE, "code": "numerisation", "display": "Numérisation"}]},
        "agent": [{"who": reference("Practitioner", agent), "onBehalfOf": reference("Organization", etablissement)}],
        "reason": [
            {
                "coding": [{"system": systemes.PIECE_D_IDENTITE, "code": piece, "display": libelle}],
                "text": f"Identité vérifiée : {libelle}",
            }
        ],
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


def _id_si_reference_a(ref: dict[str, str] | None, type_: str) -> str | None:
    """L'identifiant de `ref` quand elle désigne une ressource de type `type_` ; None sinon."""
    return id_de(ref) if ref and ref.get("reference", "").startswith(f"{type_}/") else None


class DepotIncoherent(ValueError):
    """L'ouverture d'un Dépôt ne dit pas son patient ou son agent : le noyau tient une trace mal formée."""


async def ouverture_du_depot(fhir: ClientFhir, depot: str) -> OuvertureDeDepot | None:
    """L'ouverture du Dépôt `depot`, lue dans ses AuditEvent, et s'il est clos ; None pour un Dépôt inconnu.
    `DepotIncoherent` quand l'ouverture ne dit pas son patient ou son agent : rien ne s'écrit alors au hasard."""
    traces = await fhir.chercher("AuditEvent", {"_tag": f"{systemes.DEPOT}|{depot}"})
    ouverture = next((t for t in traces if t.get("action") == "C"), None)
    if not ouverture:
        return None
    agent = next(iter(ouverture.get("agent", [])), {})
    usage = next(iter(agent.get("purposeOfUse", [])), {})
    patient = next(
        (p for p in (_id_si_reference_a(e.get("what"), "Patient") for e in ouverture.get("entity", [])) if p), None
    )
    qui = _id_si_reference_a(agent.get("who"), "Practitioner")
    if not patient or not qui:
        raise DepotIncoherent("ouverture de dépôt sans patient ou sans agent")
    clos = any(t.get("action") == "U" for t in traces) or bool(
        await fhir.chercher("Provenance", {"_tag": f"{systemes.DEPOT}|{depot}"})
    )
    return OuvertureDeDepot(
        depot=depot,
        patient=patient,
        agent=qui,
        etablissement=_id_si_reference_a(ouverture.get("source", {}).get("observer"), "Organization"),
        piece=str(usage.get("text", "")),
        reprise=_porte_l_etiquette(ouverture, etiquette_d_origine("reprise")),
        clos=clos,
    )


def identite_au_guichet(patient: Ressource) -> tuple[str, str, str | None]:
    """Nom, prénoms et année de naissance d'un Patient : tout ce que le guichet de numérisation en voit."""
    nom = next(iter(patient.get("name", [])), {})
    naissance = patient.get("birthDate")
    return str(nom.get("family", "")), " ".join(nom.get("given", [])), str(naissance)[:4] if naissance else None
