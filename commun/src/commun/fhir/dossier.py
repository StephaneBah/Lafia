"""Ce que tout service du dossier clinique partage : trouver un patient, tracer un accès, numéroter.

Les formes des ressources cliniques sont le contrat de docs/specs/F3-v1-complete.md ; chaque service
traduit les siennes dans `commun/fhir/<domaine>.py`.
"""

import secrets
from datetime import datetime, timezone
from typing import Literal

from commun.fhir import systemes
from commun.fhir.client import ClientFhir, Ressource

# L'alphabet du numéro d'ordonnance et du code carnet : ni 0, O, 1, I ni L.
ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"

Motif = Literal["recherche", "relation-de-soin", "acces-urgence", "citoyen", "numero-d-ordonnance", "numerisation", "relecture"]
Action = Literal["read", "create", "update"]
_ACTIONS = {"read": "R", "create": "C", "update": "U"}


def maintenant() -> str:
    """L'instant présent, au format FHIR `instant`."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def reference(type_: str, id_: str) -> dict[str, str]:
    return {"reference": f"{type_}/{id_}"}


def id_de(ref: dict[str, str] | None) -> str | None:
    """L'identifiant d'une référence `Type/id`, ou None."""
    if not ref or "reference" not in ref:
        return None
    return ref["reference"].rsplit("/", 1)[-1]


def numero(prefixe: str) -> str:
    """Un numéro lisible à voix haute : `ORD-7K4-M2P`, `REC-9QH-3TX`."""
    caracteres = "".join(secrets.choice(ALPHABET) for _ in range(6))
    return f"{prefixe}-{caracteres[:3]}-{caracteres[3:]}"


def numero_d_ordonnance() -> str:
    return numero("ORD")


def normaliser_numero(saisie: str, prefixe: str = "ORD") -> str:
    """Le numéro tel qu'il est stocké, quelle que soit sa saisie : `ord 7k4m2p` donne `ORD-7K4-M2P`."""
    brut = "".join(c for c in saisie.upper() if c.isalnum())
    if brut.startswith(prefixe):
        brut = brut[len(prefixe):]
    if len(brut) != 6:
        return saisie.strip().upper()
    return f"{prefixe}-{brut[:3]}-{brut[3:]}"


async def patient_par_npi(fhir: ClientFhir, npi: str) -> Ressource | None:
    """Le Patient dont `identifier` porte ce NPI, ou None."""
    trouves = await fhir.chercher("Patient", {"identifier": f"{systemes.NPI}|{npi}"})
    return trouves[0] if trouves else None


def npi_de(patient: Ressource) -> str | None:
    return next((i["value"] for i in patient.get("identifier", []) if i.get("system") == systemes.NPI), None)


def audit_event(
    *,
    patient: str,
    qui: dict[str, str],
    service: str,
    action: Action,
    motif: Motif,
    etablissement: str | None = None,
    raison: str | None = None,
    ressource: dict[str, str] | None = None,
    etiquettes: list[dict[str, str]] | None = None,
) -> Ressource:
    """Un accès au dossier de `patient` (identifiant de son Patient), en `AuditEvent`.

    `qui` est la référence de l'agent (`Practitioner/…`), de l'officine ou du patient lui-même ;
    `raison` le motif déclaré d'un accès d'urgence.
    """
    usage: dict[str, object] = {"coding": [{"system": systemes.MOTIF_D_ACCES, "code": motif}]}
    if raison:
        usage["text"] = raison
    source: dict[str, object] = {"site": service}
    if etablissement:
        source["observer"] = reference("Organization", etablissement)
    else:
        source["observer"] = qui
    entites: list[dict[str, object]] = [{"what": reference("Patient", patient)}]
    if ressource:
        entites.append({"what": ressource})
    evenement: Ressource = {
        "resourceType": "AuditEvent",
        "type": {"system": systemes.DICOM, "code": "110110", "display": "Patient Record"},
        "subtype": [{"system": systemes.ACTION_REST, "code": action}],
        "action": _ACTIONS[action],
        "recorded": maintenant(),
        "outcome": "0",
        "agent": [{"who": qui, "requestor": True, "purposeOfUse": [usage]}],
        "source": source,
        "entity": entites,
    }
    # Une étiquette retrouve l'accès par recherche : l'ouverture d'un Dépôt porte le sien.
    if etiquettes:
        evenement["meta"] = {"tag": etiquettes}
    return evenement


async def tracer(fhir: ClientFhir, **acces: object) -> None:
    """Écrit l'`AuditEvent` d'un accès : voir `audit_event`. Tout accès au dossier en laisse un."""
    await fhir.creer(audit_event(**acces))  # type: ignore[arg-type]
