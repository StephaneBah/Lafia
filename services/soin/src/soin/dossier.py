"""Ce que le service soin fait au noyau pour un soignant : lire un dossier, y écrire un cas, une
visite, une allergie ; chaque lecture et chaque écriture laisse son AuditEvent.

Les règles (relation de soin, catalogues, rôles) viennent de `soin.regles` ; la forme des ressources,
de `commun.fhir.soin`. Les routes (`soin.service`) ne font que traduire HTTP.
"""

from typing import Any

from commun.fhir import soin as fhir_soin
from commun.fhir.client import ClientFhir, Ressource
from commun.fhir.client import ecriture
from commun.fhir.dossier import Action, Motif, id_de, maintenant, numero_d_ordonnance, patient_par_npi, reference, tracer
from commun.jeton import Agent
from soin.regles import relation, visite as regles_visite

SERVICE = "soin"


class PatientInconnu(Exception):
    pass


class SansRelationDeSoin(Exception):
    pass


class CasInconnu(Exception):
    pass


class CasClos(Exception):
    pass


async def _tracer(
    fhir: ClientFhir,
    soignant: Agent,
    patient: str,
    action: Action,
    motif: Motif = "relation-de-soin",
    raison: str | None = None,
    ressource: dict[str, str] | None = None,
) -> None:
    await tracer(
        fhir,
        patient=patient,
        qui=reference("Practitioner", soignant.sub),
        service=SERVICE,
        action=action,
        motif=motif,
        etablissement=soignant.etablissement,
        raison=raison,
        ressource=ressource,
    )


async def _patient(fhir: ClientFhir, npi: str) -> Ressource:
    patient = await patient_par_npi(fhir, npi)
    if patient is None:
        raise PatientInconnu()
    return patient


async def _cas_et_visites(fhir: ClientFhir, patient: str) -> tuple[list[Ressource], list[Ressource]]:
    cas = await fhir.chercher("EpisodeOfCare", {"patient": f"Patient/{patient}"})
    visites = await fhir.chercher("Encounter", {"patient": f"Patient/{patient}"})
    return cas, visites


async def _allergies(fhir: ClientFhir, patient: str) -> list[dict[str, Any]]:
    trouvees = await fhir.chercher("AllergyIntolerance", {"patient": f"Patient/{patient}"})
    return [fhir_soin.resume_allergie(a) for a in trouvees]


class _Noms:
    """Les noms des établissements et des soignants cités, lus une fois par requête."""

    def __init__(self, fhir: ClientFhir) -> None:
        self._fhir = fhir
        self._lus: dict[str, str] = {}

    async def de(self, ref: dict[str, str] | None) -> str:
        if not ref or "reference" not in ref:
            return ""
        cle = ref["reference"]
        if cle not in self._lus:
            type_, id_ = cle.split("/", 1)
            ressource = await self._fhir.lire(type_, id_)
            if type_ == "Organization":
                self._lus[cle] = (ressource or {}).get("name", id_)
            else:
                self._lus[cle] = fhir_soin.nom_de_personne(ressource) or id_
        return self._lus[cle]


async def tarifs(fhir: ClientFhir, etablissement: str) -> dict[str, Ressource]:
    """Les tarifs de l'établissement, par code du catalogue."""
    tous = await fhir.chercher("ChargeItemDefinition", {"status": "active"})
    return {
        code: t
        for t in tous
        if fhir_soin.etablissement_du_tarif(t) == etablissement and (code := fhir_soin.code_du_catalogue(t))
    }


async def catalogue(fhir: ClientFhir, etablissement: str) -> dict[str, Any]:
    produits = await tarifs(fhir, etablissement)
    return {
        "produits": sorted(
            (
                {
                    "code": code,
                    "libelle": t["code"].get("text", code),
                    "prix": fhir_soin.prix_du_tarif(t),
                    "atc": fhir_soin.code_atc(t),
                }
                for code, t in produits.items()
            ),
            key=lambda p: p["code"],
        ),
        "mesures": [{"code": m.code, "libelle": m.libelle, "unite": m.unite} for m in fhir_soin.MESURES.values()],
        "diagnostics": [{"code": d.code, "libelle": d.libelle} for d in fhir_soin.DIAGNOSTICS.values()],
    }


async def fiche(fhir: ClientFhir, soignant: Agent, npi: str) -> dict[str, Any]:
    """Identité, allergies et titres des cas : rien de clinique. Lecture tracée."""
    patient = await _patient(fhir, npi)
    cas, visites = await _cas_et_visites(fhir, patient["id"])
    noms = _Noms(fhir)
    await _tracer(fhir, soignant, patient["id"], "read")
    return {
        "patient": fhir_soin.resume_patient(patient),
        "allergies": await _allergies(fhir, patient["id"]),
        "cas": [
            {
                "id": c["id"],
                "motif": fhir_soin.motif_du_cas(c),
                "statut": "en-cours" if c.get("status") == "active" else "termine",
                "etablissement": await noms.de(c.get("managingOrganization")),
                "etablissement_id": id_de(c.get("managingOrganization")),
                "debut": c.get("period", {}).get("start"),
                "de_mon_etablissement": relation.cas_de_l_etablissement(c, visites, soignant.etablissement),
            }
            for c in sorted(cas, key=lambda c: c.get("period", {}).get("start", ""), reverse=True)
        ],
        "relation_de_soin": relation.relation_de_soin(cas, visites, soignant.etablissement),
    }


async def dossier(fhir: ClientFhir, soignant: Agent, npi: str) -> dict[str, Any]:
    """Tout le dossier, cas par cas, visite par visite. `SansRelationDeSoin` sinon. Lecture tracée."""
    patient = await _patient(fhir, npi)
    pid = patient["id"]
    cas, visites = await _cas_et_visites(fhir, pid)
    if not relation.relation_de_soin(cas, visites, soignant.etablissement):
        raise SansRelationDeSoin()
    parametres = {"patient": f"Patient/{pid}"}
    mesures = await fhir.chercher("Observation", parametres)
    diagnostics = await fhir.chercher("Condition", parametres)
    lignes = await fhir.chercher("MedicationRequest", parametres)
    await _tracer(fhir, soignant, pid, "read")

    par_visite: dict[str, dict[str, list[Ressource]]] = {}
    for genre, ressources in (("mesures", mesures), ("diagnostics", diagnostics), ("lignes", lignes)):
        for r in ressources:
            v = id_de(r.get("encounter"))
            if v:
                par_visite.setdefault(v, {}).setdefault(genre, []).append(r)

    noms = _Noms(fhir)

    async def une_visite(v: Ressource) -> dict[str, Any]:
        contenu = par_visite.get(v["id"], {})
        lignes_v = contenu.get("lignes", [])
        numero = next((n for l in lignes_v if (n := fhir_soin.numero_de_la_ligne(l))), None)
        type_ = fhir_soin.type_de_visite(v)
        return {
            "id": v["id"],
            "type": type_,
            "type_libelle": fhir_soin.TYPES_DE_VISITE.get(type_, type_),
            "urgence": v.get("class", {}).get("code") == "EMER",
            "date": v.get("period", {}).get("start"),
            "motif": (v.get("reasonCode") or [{}])[0].get("text", ""),
            "etablissement": await noms.de(v.get("serviceProvider")),
            "soignant": await noms.de((v.get("participant") or [{}])[0].get("individual")),
            "mesures": [fhir_soin.resume_mesure(m) for m in contenu.get("mesures", [])],
            "diagnostics": [fhir_soin.resume_diagnostic(d) for d in contenu.get("diagnostics", [])],
            "ordonnance": {"numero": numero, "lignes": [fhir_soin.resume_ligne(l) for l in lignes_v]}
            if lignes_v
            else None,
        }

    resultat = []
    for c in sorted(cas, key=lambda c: c.get("period", {}).get("start", ""), reverse=True):
        visites_du_cas = sorted(
            (v for v in visites if any(id_de(e) == c["id"] for e in v.get("episodeOfCare", []))),
            key=lambda v: v.get("period", {}).get("start", ""),
        )
        resultat.append(
            {
                "id": c["id"],
                "motif": fhir_soin.motif_du_cas(c),
                "statut": "en-cours" if c.get("status") == "active" else "termine",
                "etablissement": await noms.de(c.get("managingOrganization")),
                "debut": c.get("period", {}).get("start"),
                "fin": c.get("period", {}).get("end"),
                "visites": [await une_visite(v) for v in visites_du_cas],
            }
        )
    return {
        "patient": fhir_soin.resume_patient(patient),
        "npi": npi,
        "allergies": await _allergies(fhir, pid),
        "cas": resultat,
    }


async def ouvrir_cas(fhir: ClientFhir, soignant: Agent, npi: str, motif: str) -> str:
    """Un nouveau cas à l'établissement du soignant : la relation de soin est établie. Tracé."""
    patient = await _patient(fhir, npi)
    cas = fhir_soin.episode_of_care(
        patient=patient["id"], etablissement=soignant.etablissement, soignant=soignant.sub, motif=motif
    )
    await fhir.transaction([ecriture(cas)])
    await _tracer(fhir, soignant, patient["id"], "create", ressource=reference("EpisodeOfCare", cas["id"]))
    return str(cas["id"])


async def _cas_actif(fhir: ClientFhir, cas_id: str) -> Ressource:
    cas = await fhir.lire("EpisodeOfCare", cas_id)
    if cas is None:
        raise CasInconnu()
    if cas.get("status") != "active":
        raise CasClos()
    return cas


async def enregistrer_visite(
    fhir: ClientFhir,
    soignant: Agent,
    cas_id: str,
    *,
    type_: fhir_soin.TypeDeVisite,
    motif: str,
    mesures: list[tuple[str, float | str, float | None]],
    diagnostic: tuple[str, bool, str | None] | None,
    ordonnance: list[tuple[str, int, float, list[str], int]],
) -> tuple[str, str | None]:
    """Une visite dans un cas actif, d'ici ou d'ailleurs : la continuer établit la relation de soin.

    Tout part en une transaction : la visite, ses mesures, son diagnostic, les lignes de son
    ordonnance sous un seul numéro. `VisiteRefusee` quand un élément sort d'un catalogue.
    """
    cas = await _cas_actif(fhir, cas_id)
    patient = id_de(cas.get("patient"))
    assert patient
    for code, valeur, valeur2 in mesures:
        regles_visite.verifier_mesure(code, valeur, valeur2)
    if diagnostic and diagnostic[0] not in fhir_soin.DIAGNOSTICS:
        raise regles_visite.VisiteRefusee(f"diagnostic hors de la liste : {diagnostic[0]}")
    tarifs_ici = await tarifs(fhir, soignant.etablissement) if ordonnance else {}
    for produit, quantite, _, moments, jours in ordonnance:
        regles_visite.verifier_ligne(produit, tarifs_ici, moments, jours, quantite)

    commun = {"patient": patient, "soignant": soignant.sub}
    rencontre = fhir_soin.encounter(
        cas=cas_id, etablissement=soignant.etablissement, type_=type_, motif=motif, **commun
    )
    ressources = [rencontre]
    for code, valeur, valeur2 in mesures:
        ressources.append(
            fhir_soin.observation(
                mesure=fhir_soin.MESURES[code], valeur=valeur, valeur2=valeur2, visite=rencontre["id"], **commun
            )
        )
    if diagnostic:
        code, confirme, note = diagnostic
        ressources.append(
            fhir_soin.condition(
                diagnostic=fhir_soin.DIAGNOSTICS[code],
                confirme=regles_visite.diagnostic_confirme(soignant.role, confirme),
                note=note,
                visite=rencontre["id"],
                **commun,
            )
        )
    numero = numero_d_ordonnance() if ordonnance else None
    for produit, quantite, dose, moments, jours in ordonnance:
        ressources.append(
            fhir_soin.medication_request(
                tarif=tarifs_ici[produit],
                quantite=quantite,
                dose=dose,
                moments=moments,
                jours=jours,
                numero=numero or "",
                visite=rencontre["id"],
                etablissement=soignant.etablissement,
                **commun,
            )
        )
    await fhir.transaction([ecriture(r) for r in ressources])
    await _tracer(fhir, soignant, patient, "create", ressource=reference("Encounter", rencontre["id"]))
    return str(rencontre["id"]), numero


async def clore_cas(fhir: ClientFhir, soignant: Agent, cas_id: str) -> None:
    """Clôt un cas : le médecin seulement, avec une relation de soin. Nouvelle version, tracée."""
    cas = await _cas_actif(fhir, cas_id)
    patient = id_de(cas.get("patient"))
    assert patient
    toutes, visites = await _cas_et_visites(fhir, patient)
    if not relation.relation_de_soin(toutes, visites, soignant.etablissement):
        raise SansRelationDeSoin()
    cas["status"] = "finished"
    cas.setdefault("period", {})["end"] = maintenant()
    await fhir.mettre_a_jour(cas)
    await _tracer(fhir, soignant, patient, "update", ressource=reference("EpisodeOfCare", cas_id))


async def declarer_allergie(fhir: ClientFhir, soignant: Agent, npi: str, code_atc: str, libelle: str) -> str:
    patient = await _patient(fhir, npi)
    cas, visites = await _cas_et_visites(fhir, patient["id"])
    if not relation.relation_de_soin(cas, visites, soignant.etablissement):
        raise SansRelationDeSoin()
    ecrite = await fhir.creer(
        fhir_soin.allergy_intolerance(patient=patient["id"], code_atc=code_atc, libelle=libelle, soignant=soignant.sub)
    )
    await _tracer(fhir, soignant, patient["id"], "create", ressource=reference("AllergyIntolerance", ecrite["id"]))
    return str(ecrite["id"])


async def acces_d_urgence(fhir: ClientFhir, soignant: Agent, npi: str, raison: str) -> tuple[str, str]:
    """Accès d'urgence : un cas neuf et sa visite EMER à l'établissement du soignant, tracés avec
    le motif `acces-urgence` et la raison déclarée. La relation de soin tient ensuite par ce cas."""
    patient = await _patient(fhir, npi)
    pid = patient["id"]
    cas = fhir_soin.episode_of_care(
        patient=pid, etablissement=soignant.etablissement, soignant=soignant.sub, motif="Accès d'urgence"
    )
    rencontre = fhir_soin.encounter(
        patient=pid,
        cas=cas["id"],
        etablissement=soignant.etablissement,
        soignant=soignant.sub,
        type_="urgence",
        motif=raison,
    )
    await fhir.transaction([ecriture(cas), ecriture(rencontre)])
    await _tracer(
        fhir, soignant, pid, "create", motif="acces-urgence", raison=raison,
        ressource=reference("Encounter", rencontre["id"]),
    )
    return str(cas["id"]), str(rencontre["id"])
