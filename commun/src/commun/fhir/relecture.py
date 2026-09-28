"""La Relecture des Documents dans le noyau (ADR 0007, 0009, 0010 ; docs/specs/F6-relecture-et-extraction.md).

Trois sortes de Tâches, trois `Task` du code `RELECTURE` :

- `relecture` : un Document à relire, le scan en `focus`, le patient en `for` (jamais montré au relecteur),
  le relecteur en `owner`, l'échéance de sa semaine. À sa première ouverture elle reçoit l'Extraction :
  le brouillon de Transcription et le texte lu en `input` (le brouillon en `valueMarkdown`, remplacé à
  chaque enregistrement : c'est l'état de travail du relecteur, pas encore une version), les propositions
  en ressources `contained`. Confirmée, elle porte en `output` la version courante de la Transcription.
  Renvoyée par le Contrôle, elle revient à son relecteur avec la note (`note[]`, marquée
  `note-de-controle`), brouillon gardé.
- `controle` : la Transcription confirmée à contrôler (`input`), le résumé des changements du relecteur,
  l'auteur de la relecture en `requester` (jamais le contrôleur), la Tâche de relecture en `partOf`. Elle
  naît sans `owner`, dans le pool des Contrôles ; un autre agent de relecture la reçoit dans sa semaine.
- `validation` : les propositions de l'Extraction, pour un soignant, une fois la Transcription relue.

Une Transcription est un `DocumentReference` de type Transcription (ADR 0010) : Markdown dans un `Binary`,
`relatesTo` `transforms` le scan et `replaces` la version d'avant, qui passe `superseded` ; `docStatus`
preliminary à la confirmation, final au Contrôle. Chaque version a son `Provenance` : `relecture` ou
`controle`, le relecteur en agent, le scan en source.

Une Tâche est un objet de travail, pas une entrée du dossier : elle change d'état en nouvelles versions,
son historique reste lisible. `executionPeriod.end` date la confirmation, le Contrôle ou la clôture ;
`businessStatus` en dit l'issue.
"""

import base64
import copy
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal

from commun.extraction import TYPES_DE_PROPOSITION, Extraction, Modele
from commun.fhir import systemes
from commun.fhir.client import ClientFhir, Ressource
from commun.fhir.documents import avec_origine, etiquette_d_origine
from commun.fhir.dossier import id_de, maintenant, reference

Etape = Literal["relecture", "controle", "validation"]
ETAPES: dict[str, str] = {"relecture": "Relecture", "controle": "Contrôle", "validation": "Validation clinique"}
Decision = Literal["accepter", "corriger", "rejeter"]
"""La décision d'un soignant sur une proposition, à la validation."""
DecisionDeControle = Literal["accepter", "renvoyer"]
Raison = Literal["non-medical", "doublon"]
RAISONS: dict[str, str] = {"non-medical": "Pas un document médical", "doublon": "Déjà numérisé"}
Issue = Literal["confirmee", "relue", "renvoyee", "acceptee", "non-medical", "doublon"]
ISSUES: dict[str, str] = {
    "confirmee": "Confirmée, en attente du Contrôle",
    "relue": "Relue",
    "renvoyee": "Renvoyée par le Contrôle",
    "acceptee": "Acceptée",
    **RAISONS,
}

TYPE_TRANSCRIPTION = {
    "coding": [{"system": systemes.TYPE_DE_DOCUMENT, "code": "transcription", "display": "Transcription"}],
    "text": "Transcription",
}
"""Le type d'une Transcription, dans le système des types de Document : un Document dérivé, pas un papier."""
FORMAT_DE_TRANSCRIPTION = "text/markdown; charset=utf-8"
NOTE_DE_CONTROLE = f"{systemes.LAFIA}/StructureDefinition/note-de-controle"

_MODELE = "Modèle de lecture"
_PROPOSITION = "Proposition"
_TEXTE_LU = "Texte lu"
_BROUILLON = "Brouillon de Transcription"
_RESUME = "Résumé des changements"
_TRANSCRIPTION = "Transcription"
_ENTREE_VALIDEE = "Entrée validée"


# La semaine.


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


def semaine_de(tache: Ressource) -> str | None:
    """La semaine d'une Tâche : la plus récente de ses étiquettes, le noyau gardant celles d'avant quand
    une Tâche réassignée en reçoit une nouvelle."""
    semaines = [
        str(e.get("code")) for e in tache.get("meta", {}).get("tag", []) if e.get("system") == systemes.SEMAINE_DE_RELECTURE
    ]
    return max(semaines) if semaines else None


def reassignee(tache: Ressource, relecteur: str, jour: date) -> Ressource:
    """La Tâche assignée à `relecteur` pour la semaine de `jour` : une Tâche de relecture restée ouverte une
    semaine passée, un Contrôle tiré du pool, ou une relecture renvoyée qui revient à son relecteur."""
    suivante = copy.deepcopy(tache)
    etiquettes = [e for e in tache.get("meta", {}).get("tag", []) if e.get("system") != systemes.SEMAINE_DE_RELECTURE]
    suivante["meta"] = {"tag": [*etiquettes, etiquette_de_semaine(semaine(jour))]}
    suivante["owner"] = reference("Practitioner", relecteur)
    suivante["restriction"] = {"period": {"end": fin_de_semaine(jour)}}
    return suivante


# Lire une Tâche.


def _code_d_etape(etape: Etape) -> dict[str, Any]:
    return {"coding": [{"system": systemes.RELECTURE, "code": etape, "display": ETAPES[etape]}], "text": ETAPES[etape]}


def etape_de(tache: Ressource) -> Etape | None:
    """L'étape d'une Tâche ; None pour une Tâche d'une forme passée (le triage de la première F6)."""
    code = next((c.get("code") for c in tache.get("code", {}).get("coding", []) if c.get("system") == systemes.RELECTURE), None)
    return code if code in ETAPES else None  # type: ignore[return-value]


def est_ouverte(tache: Ressource) -> bool:
    return tache.get("status") in ("ready", "in-progress")


def patient_de(tache: Ressource) -> str | None:
    return id_de(tache.get("for"))


def document_de(tache: Ressource) -> str | None:
    """Le scan que vise la Tâche."""
    return id_de(tache.get("focus"))


def relecteur_de(tache: Ressource) -> str | None:
    return id_de(tache.get("owner"))


def auteur_de(controle: Ressource) -> str | None:
    """L'agent de relecture qui a confirmé la Transcription qu'un Contrôle vise : jamais son contrôleur."""
    return id_de(controle.get("requester"))


def relecture_de(tache: Ressource) -> str | None:
    """La Tâche de relecture dont un Contrôle ou une validation découle."""
    return next((id_de(p) for p in tache.get("partOf", [])), None)


def echeance_de(tache: Ressource) -> str | None:
    return tache.get("restriction", {}).get("period", {}).get("end")


def issue_de(tache: Ressource) -> str | None:
    return next((c.get("code") for c in tache.get("businessStatus", {}).get("coding", [])), None)


def fin_de(tache: Ressource) -> str | None:
    """Quand la Tâche a été confirmée, contrôlée ou close."""
    return tache.get("executionPeriod", {}).get("end")


def _entree(tache: Ressource, nom: str) -> dict[str, Any] | None:
    return next((i for i in tache.get("input", []) if i.get("type", {}).get("text") == nom), None)


def _sans_entree(tache: Ressource, *noms: str) -> list[dict[str, Any]]:
    return [i for i in tache.get("input", []) if i.get("type", {}).get("text") not in noms]


def brouillon_de(tache: Ressource) -> str | None:
    """Le brouillon de Transcription d'une Tâche de relecture : celui de l'Extraction, puis du relecteur."""
    return (_entree(tache, _BROUILLON) or {}).get("valueMarkdown")


def texte_lu_de(tache: Ressource) -> str | None:
    """Le texte brut lu par l'Extraction."""
    return (_entree(tache, _TEXTE_LU) or {}).get("valueString")


def resume_de(tache: Ressource) -> str | None:
    """Le résumé des changements que le relecteur a donné à sa dernière confirmation."""
    return (_entree(tache, _RESUME) or {}).get("valueString")


def transcription_de(tache: Ressource) -> str | None:
    """La version de la Transcription que porte la Tâche : en sortie d'une relecture confirmée ou d'une
    validation, en entrée d'un Contrôle."""
    for porteur in (*tache.get("output", []), *tache.get("input", [])):
        if porteur.get("type", {}).get("text") == _TRANSCRIPTION:
            return id_de(porteur.get("valueReference"))
    return None


def modele_de(tache: Ressource) -> Modele | None:
    valeur = (_entree(tache, _MODELE) or {}).get("valueString")
    if not valeur or ":" not in valeur:
        return None
    nom, version = valeur.split(":", 1)
    return Modele(nom=nom, version=version)


@dataclass(frozen=True)
class NoteDeControle:
    date: str | None
    texte: str


def notes_de_controle(tache: Ressource) -> list[NoteDeControle]:
    """Les notes des Contrôles qui ont renvoyé la Tâche de relecture, dans l'ordre."""
    return [
        NoteDeControle(date=n.get("time"), texte=n.get("text", ""))
        for n in tache.get("note", [])
        if any(e.get("url") == NOTE_DE_CONTROLE for e in n.get("extension", []))
    ]


# Les Tâches, d'une étape à l'autre.


def _issue(issue: Issue) -> dict[str, Any]:
    return {"coding": [{"system": systemes.ISSUE_DE_RELECTURE, "code": issue, "display": ISSUES[issue]}], "text": ISSUES[issue]}


def _terminee(tache: Ressource, statut: str, issue: Issue) -> Ressource:
    suivante = copy.deepcopy(tache)
    instant = maintenant()
    suivante["status"] = statut
    suivante["businessStatus"] = _issue(issue)
    suivante["lastModified"] = instant
    suivante["executionPeriod"] = {**tache.get("executionPeriod", {}), "end": instant}
    return suivante


def tache_de_relecture(*, document: str, patient: str, relecteur: str, jour: date) -> Ressource:
    """Une Tâche de relecture du Document `document`, assignée à `relecteur` pour la semaine de `jour`."""
    return {
        "resourceType": "Task",
        "meta": {"tag": [etiquette_de_semaine(semaine(jour))]},
        "status": "ready",
        "intent": "order",
        "code": _code_d_etape("relecture"),
        "focus": reference("DocumentReference", document),
        "for": reference("Patient", patient),
        "owner": reference("Practitioner", relecteur),
        "authoredOn": maintenant(),
        "restriction": {"period": {"end": fin_de_semaine(jour)}},
    }


def avec_extraction(tache: Ressource, extraction: Extraction) -> Ressource:
    """La Tâche de relecture ouverte avec son Extraction : le brouillon et le texte lu en entrées, les
    propositions en ressources contenues (`#p1`, `#p2`…), chacune citée par une entrée (une ressource
    contenue que rien ne cite n'est pas conforme, dom-3, et le noyau la perdrait), le modèle en entrée.
    Elle passe en cours."""
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
    if contenues:
        suivante["contained"] = contenues
    else:
        suivante.pop("contained", None)
    suivante["input"] = [
        *_sans_entree(tache, _MODELE, _PROPOSITION, _TEXTE_LU, _BROUILLON),
        {"type": {"text": _MODELE}, "valueString": f"{extraction.modele.nom}:{extraction.modele.version}"},
        {"type": {"text": _TEXTE_LU}, "valueString": extraction.texte},
        {"type": {"text": _BROUILLON}, "valueMarkdown": extraction.transcription},
        *[{"type": {"text": _PROPOSITION}, "valueReference": {"reference": f"#{c['id']}"}} for c in contenues],
    ]
    instant = maintenant()
    suivante["status"] = "in-progress"
    suivante["lastModified"] = instant
    suivante["executionPeriod"] = {"start": instant}
    return suivante


def avec_brouillon(tache: Ressource, markdown: str) -> Ressource:
    """La Tâche de relecture portant le brouillon corrigé du relecteur, qui remplace le précédent."""
    suivante = copy.deepcopy(tache)
    entrees = _sans_entree(tache, _BROUILLON)
    suivante["input"] = [*entrees, {"type": {"text": _BROUILLON}, "valueMarkdown": markdown}]
    suivante["status"] = "in-progress"
    suivante["lastModified"] = maintenant()
    return suivante


def confirmee(tache: Ressource, *, transcription: dict[str, str], resume: str, relue: bool) -> Ressource:
    """La Tâche de relecture confirmée : close, la version écrite en sortie, le résumé en entrée. Relue
    d'emblée quand aucun Contrôle ne suit."""
    suivante = _terminee(tache, "completed", "relue" if relue else "confirmee")
    suivante["input"] = [*_sans_entree(tache, _RESUME), {"type": {"text": _RESUME}, "valueString": resume}]
    suivante["output"] = [{"type": {"text": _TRANSCRIPTION}, "valueReference": transcription}]
    return suivante


def relue(tache: Ressource, transcription: dict[str, str]) -> Ressource:
    """La Tâche de relecture dont la Transcription vient d'être acceptée au Contrôle."""
    suivante = copy.deepcopy(tache)
    suivante["businessStatus"] = _issue("relue")
    suivante["lastModified"] = maintenant()
    suivante["output"] = [{"type": {"text": _TRANSCRIPTION}, "valueReference": transcription}]
    return suivante


def renvoyee(tache: Ressource, *, note: str, controleur: str, jour: date) -> Ressource:
    """La Tâche de relecture renvoyée par le Contrôle : de nouveau à faire par son relecteur, dans sa
    semaine, la note à la suite des autres, le brouillon gardé."""
    relecteur = relecteur_de(tache) or ""
    suivante = reassignee(tache, relecteur, jour)
    suivante["status"] = "ready"
    suivante["businessStatus"] = _issue("renvoyee")
    suivante["lastModified"] = maintenant()
    suivante["note"] = [
        *tache.get("note", []),
        {
            "extension": [{"url": NOTE_DE_CONTROLE, "valueBoolean": True}],
            "authorReference": reference("Practitioner", controleur),
            "time": maintenant(),
            "text": note,
        },
    ]
    return suivante


def inutilisable(tache: Ressource, raison: Raison) -> Ressource:
    """La Tâche de relecture close sans Transcription : le Document n'est pas médical, ou déjà numérisé."""
    return _terminee(tache, "rejected", raison)


def tache_de_controle(
    *, id_: str, relecture: Ressource, transcription: dict[str, str], resume: str
) -> Ressource:
    """Le Contrôle d'une Transcription confirmée : sans `owner`, au pool des Contrôles ; l'auteur de la
    relecture en `requester`, qui ne le recevra jamais."""
    return {
        "resourceType": "Task",
        "id": id_,
        "status": "ready",
        "intent": "order",
        "code": _code_d_etape("controle"),
        "focus": copy.deepcopy(relecture["focus"]),
        "for": copy.deepcopy(relecture["for"]),
        "requester": copy.deepcopy(relecture["owner"]),
        "partOf": [reference("Task", relecture["id"])],
        "authoredOn": maintenant(),
        "input": [
            {"type": {"text": _TRANSCRIPTION}, "valueReference": transcription},
            {"type": {"text": _RESUME}, "valueString": resume},
        ],
    }


def controlee(controle: Ressource, decision: DecisionDeControle) -> Ressource:
    return _terminee(controle, "completed", "acceptee" if decision == "accepter" else "renvoyee")


def tache_de_validation(*, id_: str, relecture: Ressource, transcription: dict[str, str]) -> Ressource | None:
    """La validation clinique des propositions d'une Tâche de relecture dont la Transcription est relue :
    au pool des soignants, sans `owner`. None quand l'Extraction n'a rien proposé."""
    if not relecture.get("contained"):
        return None
    return {
        "resourceType": "Task",
        "id": id_,
        "status": "ready",
        "intent": "order",
        "code": _code_d_etape("validation"),
        "focus": copy.deepcopy(relecture["focus"]),
        "for": copy.deepcopy(relecture["for"]),
        "partOf": [reference("Task", relecture["id"])],
        "authoredOn": maintenant(),
        "contained": copy.deepcopy(relecture["contained"]),
        "input": [copy.deepcopy(i) for i in relecture.get("input", []) if i.get("type", {}).get("text") in (_MODELE, _TEXTE_LU, _PROPOSITION)],
        "output": [{"type": {"text": _TRANSCRIPTION}, "valueReference": transcription}],
    }


def prise(tache: Ressource, soignant: str) -> Ressource:
    """La Tâche de validation qu'un soignant prend : elle est à lui, en cours."""
    suivante = copy.deepcopy(tache)
    suivante["owner"] = reference("Practitioner", soignant)
    suivante["status"] = "in-progress"
    return suivante


# La Transcription (ADR 0010).


def est_une_transcription(ressource: Ressource) -> bool:
    return any(
        c.get("system") == systemes.TYPE_DE_DOCUMENT and c.get("code") == "transcription"
        for c in ressource.get("type", {}).get("coding", [])
    )


def binary_de_transcription(markdown: str, patient: str) -> Ressource:
    return {
        "resourceType": "Binary",
        "contentType": FORMAT_DE_TRANSCRIPTION,
        "securityContext": reference("Patient", patient),
        "data": base64.b64encode(markdown.encode()).decode(),
    }


def transcription(
    *,
    scan: Ressource,
    auteurs: list[str],
    binary: str,
    taille: int,
    relue: bool,
    precedente: str | None,
) -> Ressource:
    """Une version de la Transcription du scan : `relue` au Contrôle, préliminaire avant. Elle transforme le
    scan et remplace `precedente`. Son origine est l'Extraction, que les relecteurs ont corrigée : leurs
    Provenance le disent."""
    relations = [{"code": "transforms", "target": reference("DocumentReference", scan["id"])}]
    if precedente:
        relations.append({"code": "replaces", "target": reference("DocumentReference", precedente)})
    ressource: Ressource = {
        "resourceType": "DocumentReference",
        "status": "current",
        "docStatus": "final" if relue else "preliminary",
        "type": copy.deepcopy(TYPE_TRANSCRIPTION),
        "subject": copy.deepcopy(scan["subject"]),
        "date": maintenant(),
        "author": [reference("Practitioner", a) for a in auteurs],
        "relatesTo": relations,
        "content": [
            {"attachment": {"contentType": FORMAT_DE_TRANSCRIPTION, "url": f"Binary/{binary}", "size": taille, "title": "Transcription"}}
        ],
    }
    if scan.get("context", {}).get("period"):
        ressource["context"] = {"period": copy.deepcopy(scan["context"]["period"])}
    return avec_origine(ressource, "extraction")


def binary_de(version: Ressource) -> str | None:
    """Le Binary qui porte le Markdown d'une version de la Transcription."""
    url = next(iter(version.get("content", [])), {}).get("attachment", {}).get("url", "")
    return url.rsplit("/", 1)[-1] or None


def remplacee(version: Ressource) -> Ressource:
    """La version d'avant, qu'une nouvelle remplace (ADR 0007) : elle reste lisible, `superseded`."""
    suivante = copy.deepcopy(version)
    suivante["status"] = "superseded"
    return suivante


def provenance_de_relecture(
    *, cible: dict[str, str], scan: str, relecteur: str, activite: Literal["relecture", "controle"], modele: Modele | None
) -> Ressource:
    """Qui a fait une version de la Transcription : le relecteur qui l'a confirmée, ou celui qui l'a
    contrôlée ; le scan en source ; à la relecture, le modèle dont le brouillon est parti."""
    libelle = ETAPES[activite]
    agents: list[dict[str, Any]] = [
        {"type": {"text": "Relu par" if activite == "relecture" else "Contrôlé par"}, "who": reference("Practitioner", relecteur)}
    ]
    if modele and activite == "relecture":
        agents.append({"type": {"text": "Lu par"}, "who": reference("Device", device(modele)["id"])})
    return {
        "resourceType": "Provenance",
        "target": [cible],
        "recorded": maintenant(),
        "activity": {"coding": [{"system": systemes.RELECTURE, "code": activite, "display": libelle}], "text": libelle},
        "agent": agents,
        "entity": [{"role": "source", "what": reference("DocumentReference", scan)}],
    }


async def markdown_de(fhir: ClientFhir, version: Ressource) -> str | None:
    """Le Markdown d'une version de la Transcription, lu dans son Binary."""
    binary = binary_de(version)
    lu = await fhir.lire("Binary", binary) if binary else None
    return base64.b64decode(lu.get("data", "")).decode() if lu else None


async def transcription_relue(fhir: ClientFhir, scan: str) -> Ressource | None:
    """La Transcription relue (`docStatus` final, courante) d'un scan, ou None tant qu'elle ne l'est pas.
    Ce que soin et citoyen montrent ; une version préliminaire ne sort jamais de la relecture."""
    trouvees = await fhir.chercher("DocumentReference", {"relatesto": f"DocumentReference/{scan}", "status": "current"})
    relues = [d for d in trouvees if est_une_transcription(d) and d.get("docStatus") == "final"]
    return max(relues, key=lambda d: d.get("date", ""), default=None)


# Le modèle de lecture, et les propositions à la validation (ADR 0009).


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


def proposition_de(tache: Ressource, proposition: str) -> Ressource | None:
    """La proposition `proposition` (`p1`) de la Tâche, telle que le modèle l'a rendue."""
    return next((copy.deepcopy(r) for r in tache.get("contained", []) if r.get("id") == proposition), None)


def apres_validation(
    tache: Ressource, decisions: dict[str, Decision], soignant: str, entrees: list[dict[str, str]]
) -> Ressource:
    """La Tâche close par la validation : chaque proposition garde la décision du soignant (les rejetées
    restent là, pour mesurer le modèle), les entrées écrites au dossier s'ajoutent aux sorties."""
    suivante = copy.deepcopy(tache)
    for contenue in suivante.get("contained", []):
        contenue.setdefault("extension", []).append(
            {"url": f"{systemes.LAFIA}/StructureDefinition/decision", "valueCode": decisions.get(contenue.get("id", ""), "rejeter")}
        )
    suivante["status"] = "completed"
    suivante["output"] = [
        *tache.get("output", []),
        *[{"type": {"text": _ENTREE_VALIDEE}, "valueReference": ref} for ref in entrees],
    ]
    retenues = sum(1 for d in decisions.values() if d != "rejeter")
    rejetees = len(tache.get("contained", [])) - retenues
    suivante["note"] = [
        *tache.get("note", []),
        {
            "authorReference": reference("Practitioner", soignant),
            "time": maintenant(),
            "text": f"Validation : {retenues} retenue(s), {rejetees} rejetée(s)",
        },
    ]
    return suivante


def entrees_validees(tache: Ressource) -> list[str]:
    """Les références (`Condition/123`) des entrées qu'une validation a écrites au dossier."""
    return [
        o.get("valueReference", {}).get("reference", "")
        for o in tache.get("output", [])
        if o.get("type", {}).get("text") == _ENTREE_VALIDEE
    ]


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
        if valeur_corrigee is not None:
            # Le libellé corrigé ne répond plus aux codes proposés : il reste seul.
            entree["code"] = {"text": valeur_corrigee}
    elif type_ == "AllergyIntolerance":
        entree["patient"] = sujet
        entree["recorder"] = auteur
        entree["recordedDate"] = maintenant()
        if valeur_corrigee is not None:
            entree["code"] = {"text": valeur_corrigee}
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


# Chercher les Tâches d'un relecteur.


async def taches_de(fhir: ClientFhir, relecteur: str, valeur_de_semaine: str) -> list[Ressource]:
    """Les Tâches d'un relecteur étiquetées de cette semaine."""
    return await fhir.chercher(
        "Task",
        {"owner": f"Practitioner/{relecteur}", "_tag": f"{systemes.SEMAINE_DE_RELECTURE}|{valeur_de_semaine}"},
    )


async def taches_ouvertes_de(fhir: ClientFhir, relecteur: str) -> list[Ressource]:
    """Les Tâches à faire ou en cours d'un relecteur, de quelque semaine qu'elles soient."""
    return await fhir.chercher("Task", {"owner": f"Practitioner/{relecteur}", "status": "ready,in-progress"})
