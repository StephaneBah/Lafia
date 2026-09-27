"""La Relecture des Documents dans le noyau (ADR 0007, 0009 ; docs/specs/F6-relecture-et-extraction.md).

Une Tâche de relecture est un `Task` : le Document en `focus`, le patient en `for` (jamais montré au
relecteur), le relecteur en `owner`, l'échéance de sa semaine. Les propositions d'une Extraction vivent
dans la Tâche, en ressources `contained`, jusqu'à la validation d'un soignant : rien n'entre au dossier
avant. Une Tâche est un objet de travail, pas une entrée du dossier : elle change d'état en nouvelles
versions, son historique reste lisible.
"""

import base64
import copy
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal

from commun.extraction import TYPES_DE_PROPOSITION, Extraction, Modele, Proposition
from commun.fhir import systemes
from commun.fhir.client import ClientFhir, Ressource
from commun.fhir.documents import avec_origine, etiquette_d_origine
from commun.fhir.dossier import id_de, maintenant, reference

Etape = Literal["triage", "validation"]
Verdict = Literal["utilisable", "illisible", "non-medical", "mauvais-type", "doublon"]
VERDICTS: dict[Verdict, str] = {
    "utilisable": "Utilisable",
    "illisible": "Illisible",
    "non-medical": "Pas un document médical",
    "mauvais-type": "Type à corriger",
    "doublon": "Déjà numérisé",
}
Decision = Literal["accepter", "corriger", "rejeter"]


def semaine(jour: date) -> str:
    """La semaine ISO d'un jour, telle qu'une Tâche la porte : `2026-W39`."""
    annee, numero, _ = jour.isocalendar()
    return f"{annee}-W{numero:02d}"


def fin_de_semaine(jour: date) -> str:
    """Le dimanche soir de la semaine de `jour`, échéance d'une Tâche assignée ce jour-là."""
    dimanche = jour + timedelta(days=6 - jour.weekday())
    return datetime(dimanche.year, dimanche.month, dimanche.day, 23, 59, 59, tzinfo=timezone.utc).isoformat()


def etiquette_de_semaine(valeur: str) -> dict[str, str]:
    return {"system": systemes.SEMAINE_DE_RELECTURE, "code": valeur}


def tache_de_relecture(*, document: str, patient: str, relecteur: str, jour: date) -> Ressource:
    """Une Tâche de triage du Document `document`, assignée à `relecteur` pour la semaine de `jour`."""
    return {
        "resourceType": "Task",
        "meta": {"tag": [etiquette_de_semaine(semaine(jour))]},
        "status": "ready",
        "intent": "order",
        "code": _code_d_etape("triage"),
        "focus": reference("DocumentReference", document),
        "for": reference("Patient", patient),
        "owner": reference("Practitioner", relecteur),
        "authoredOn": maintenant(),
        "restriction": {"period": {"end": fin_de_semaine(jour)}},
    }


def _code_d_etape(etape: Etape) -> dict[str, Any]:
    libelle = {"triage": "Triage", "validation": "Validation clinique"}[etape]
    return {"coding": [{"system": systemes.RELECTURE, "code": etape, "display": libelle}], "text": libelle}


def etape_de(tache: Ressource) -> Etape:
    code = next(iter(tache.get("code", {}).get("coding", [])), {}).get("code")
    return "validation" if code == "validation" else "triage"


def apres_triage(tache: Ressource, verdict: Verdict, relecteur: str) -> Ressource:
    """La Tâche après le triage : un Document utilisable passe en validation, rendue au pool des
    soignants (sans `owner`) ; tout autre verdict clôt la Tâche."""
    suivante = copy.deepcopy(tache)
    suivante["businessStatus"] = {
        "coding": [{"system": systemes.VERDICT_DE_TRIAGE, "code": verdict, "display": VERDICTS[verdict]}],
        "text": VERDICTS[verdict],
    }
    suivante["note"] = [*tache.get("note", []), {"authorReference": reference("Practitioner", relecteur), "time": maintenant(), "text": f"Triage : {VERDICTS[verdict]}"}]
    if verdict == "utilisable":
        suivante["code"] = _code_d_etape("validation")
        suivante["status"] = "ready"
        suivante.pop("owner", None)
    else:
        suivante["status"] = "completed"
    return suivante


def avec_extraction(tache: Ressource, extraction: Extraction, texte_document: str) -> Ressource:
    """La Tâche portant une Extraction : ses propositions en ressources contenues (`#p1`, `#p2`…),
    le Document de texte en sortie, le modèle en entrée."""
    suivante = copy.deepcopy(tache)
    contenues = []
    for rang, proposition in enumerate(extraction.propositions, start=1):
        if proposition.ressource.get("resourceType") not in TYPES_DE_PROPOSITION:
            continue
        brouillon = copy.deepcopy(proposition.ressource)
        brouillon["id"] = f"p{rang}"
        brouillon.setdefault("extension", []).append(
            {"url": f"{systemes.LAFIA}/StructureDefinition/confiance", "valueDecimal": proposition.confiance}
        )
        if proposition.extrait:
            brouillon["extension"].append({"url": f"{systemes.LAFIA}/StructureDefinition/extrait", "valueString": proposition.extrait})
        contenues.append(brouillon)
    suivante["contained"] = contenues
    suivante["input"] = [
        {
            "type": {"text": "Modèle de lecture"},
            "valueString": f"{extraction.modele.nom}:{extraction.modele.version}",
        }
    ]
    suivante["output"] = [{"type": {"text": "Texte lu"}, "valueReference": reference("DocumentReference", texte_document)}]
    return suivante


def modele_de(tache: Ressource) -> Modele | None:
    valeur = next((i.get("valueString") for i in tache.get("input", []) if i.get("type", {}).get("text") == "Modèle de lecture"), None)
    if not valeur or ":" not in valeur:
        return None
    nom, version = valeur.split(":", 1)
    return Modele(nom=nom, version=version)


def device(modele: Modele) -> Ressource:
    """Le modèle de lecture en Device, sous un identifiant fixe : l'écrire deux fois ne le double pas."""
    cle = f"{modele.nom}-{modele.version}".lower().replace(".", "-")
    return {
        "resourceType": "Device",
        "id": f"modele-{cle}",
        "identifier": [{"system": systemes.MODELE_DE_LECTURE, "value": f"{modele.nom}:{modele.version}"}],
        "deviceName": [{"name": modele.nom, "type": "model-name"}],
        "version": [{"value": modele.version}],
    }


def document_de_texte(*, scan: str, patient: str, texte: str, modele: Modele, binary: str) -> Ressource:
    """Le texte lu d'un Document, en Document dérivé (`transforms` le scan)."""
    ressource: Ressource = {
        "resourceType": "DocumentReference",
        "status": "current",
        "docStatus": "preliminary",
        "type": {"text": "Texte lu"},
        "category": [{"coding": [{"system": systemes.ORIGINE, "code": "extraction", "display": "Extraction"}], "text": "Extraction"}],
        "subject": reference("Patient", patient),
        "date": maintenant(),
        "author": [reference("Device", device(modele)["id"])],
        "relatesTo": [{"code": "transforms", "target": reference("DocumentReference", scan)}],
        "content": [{"attachment": {"contentType": "text/plain; charset=utf-8", "url": f"Binary/{binary}", "size": len(texte.encode()), "title": "Texte lu"}}],
    }
    return avec_origine(ressource, "extraction")


def binary_de_texte(texte: str, patient: str) -> Ressource:
    return {
        "resourceType": "Binary",
        "contentType": "text/plain; charset=utf-8",
        "securityContext": reference("Patient", patient),
        "data": base64.b64encode(texte.encode()).decode(),
    }


@dataclass(frozen=True)
class PropositionVue:
    """Une proposition telle que le soignant la voit : son libellé, sa valeur, la confiance du modèle."""

    id: str
    type: str
    libelle: str
    valeur: str | None
    confiance: float | None
    extrait: str | None


def propositions_de(tache: Ressource) -> list[PropositionVue]:
    return [_vue(r) for r in tache.get("contained", [])]


def _vue(r: Ressource) -> PropositionVue:
    ext = {e.get("url", "").rsplit("/", 1)[-1]: e for e in r.get("extension", [])}
    code = r.get("code") or r.get("medicationCodeableConcept") or {}
    libelle = code.get("text") or next((c.get("display") for c in code.get("coding", []) if c.get("display")), r["resourceType"])
    valeur = None
    if "valueQuantity" in r:
        q = r["valueQuantity"]
        valeur = f"{q.get('value')} {q.get('unit', '')}".strip()
    elif "valueString" in r:
        valeur = r["valueString"]
    elif r.get("dosage"):
        valeur = r["dosage"][0].get("text")
    return PropositionVue(
        id=r["id"],
        type=r["resourceType"],
        libelle=libelle,
        valeur=valeur,
        confiance=ext.get("confiance", {}).get("valueDecimal"),
        extrait=ext.get("extrait", {}).get("valueString"),
    )


def entree_validee(brouillon: Ressource, *, patient: str, soignant: str, valeur_corrigee: str | None = None) -> Ressource:
    """Une proposition acceptée (ou corrigée) devenue entrée du dossier : sujet, auteur, origine `extraction`."""
    entree = copy.deepcopy(brouillon)
    entree.pop("id", None)
    entree["extension"] = [e for e in entree.get("extension", []) if not e.get("url", "").startswith(f"{systemes.LAFIA}/StructureDefinition/")]
    if not entree["extension"]:
        entree.pop("extension")
    type_ = entree["resourceType"]
    sujet = reference("Patient", patient)
    auteur = reference("Practitioner", soignant)
    if type_ == "Observation":
        entree["subject"] = sujet
        entree["performer"] = [auteur]
        entree.setdefault("status", "final")
        if valeur_corrigee is not None and "valueQuantity" in entree:
            entree["valueQuantity"]["value"] = float(valeur_corrigee.replace(",", "."))
    elif type_ == "Condition":
        entree["subject"] = sujet
        entree["recorder"] = auteur
        entree["recordedDate"] = maintenant()
    elif type_ == "AllergyIntolerance":
        entree["patient"] = sujet
        entree["recorder"] = auteur
        entree["recordedDate"] = maintenant()
    elif type_ == "MedicationStatement":
        entree["subject"] = sujet
        entree["informationSource"] = auteur
        entree["dateAsserted"] = maintenant()
        if valeur_corrigee is not None:
            entree.setdefault("dosage", [{}])[0]["text"] = valeur_corrigee
    return avec_origine(entree, "extraction")


def provenance_d_extraction(*, cible: dict[str, str], scan: str, soignant: str, modele: Modele) -> Ressource:
    """Une entrée venue d'une Extraction : le Document lu, le soignant qui l'a acceptée, le modèle."""
    return {
        "resourceType": "Provenance",
        "meta": {"tag": [etiquette_d_origine("extraction")]},
        "target": [cible],
        "recorded": maintenant(),
        "activity": {"coding": [{"system": systemes.ORIGINE, "code": "extraction", "display": "Extraction validée"}]},
        "agent": [
            {"type": {"text": "Validé par"}, "who": reference("Practitioner", soignant)},
            {"type": {"text": "Lu par"}, "who": reference("Device", device(modele)["id"])},
        ],
        "entity": [{"role": "source", "what": reference("DocumentReference", scan)}],
    }


async def taches_de(fhir: ClientFhir, relecteur: str, valeur_de_semaine: str) -> list[Ressource]:
    return await fhir.chercher(
        "Task",
        {"owner": f"Practitioner/{relecteur}", "_tag": f"{systemes.SEMAINE_DE_RELECTURE}|{valeur_de_semaine}"},
    )


def patient_de(tache: Ressource) -> str | None:
    return id_de(tache.get("for"))


def document_de(tache: Ressource) -> str | None:
    return id_de(tache.get("focus"))
