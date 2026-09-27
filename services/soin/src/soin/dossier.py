"""Ce que le service soin fait au noyau pour un soignant : trouver un patient, lire son bandeau et
son dossier, y écrire un cas, une visite, une allergie, un antécédent, un traitement au long cours,
un groupe sanguin ; chaque lecture et chaque écriture laisse son AuditEvent.

Les règles (relation de soin, catalogues, rôles) viennent de `soin.regles` ; la forme des ressources,
écrites comme lues, de `commun.fhir.soin`. Les routes (`soin.service`) ne font que traduire HTTP.
"""

from typing import Any

from commun.fhir import documents as fhir_documents
from commun.fhir import soin as fhir_soin
from commun.fhir import systemes
from commun.fhir import transcriptions as fhir_transcriptions
from commun.fhir.client import ClientFhir, Ressource, ecriture
from commun.fhir.documents import Origine, Page, avec_origine
from commun.fhir.dossier import Action, Motif, id_de, numero_d_ordonnance, patient_par_npi, reference, tracer
from commun.jeton import Agent
from soin import modeles
from soin.regles import documents as regles_documents
from soin.regles import dossier as regles_dossier
from soin.regles import relation
from soin.regles import visite as regles_visite
from soin.regles.relation import SansRelationDeSoin

SERVICE = "soin"

__all__ = [
    "CasClos",
    "CasInconnu",
    "DocumentInconnu",
    "PageInconnue",
    "PatientInconnu",
    "SansRelationDeSoin",
    "TraitementInconnu",
    "TranscriptionInconnue",
]


class PatientInconnu(Exception):
    pass


class CasInconnu(Exception):
    pass


class CasClos(Exception):
    pass


class TraitementInconnu(Exception):
    pass


class DocumentInconnu(Exception):
    pass


class PageInconnue(Exception):
    pass


class TranscriptionInconnue(Exception):
    """Le Document n'a pas (encore) de Transcription relue."""


async def _tracer(
    fhir: ClientFhir,
    soignant: Agent,
    patient: str,
    action: Action,
    motif: Motif,
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


async def _patient(fhir: ClientFhir, patient_id: str) -> Ressource:
    patient = await fhir.lire("Patient", patient_id)
    if patient is None:
        raise PatientInconnu()
    return patient


async def _cas_et_visites(fhir: ClientFhir, patient: str) -> tuple[list[Ressource], list[Ressource]]:
    cas = await fhir.chercher("EpisodeOfCare", {"patient": f"Patient/{patient}"})
    visites = await fhir.chercher("Encounter", {"patient": f"Patient/{patient}"})
    return cas, visites


async def _motif_exige(fhir: ClientFhir, soignant: Agent, patient: str) -> Motif:
    """Le motif de la relation de soin du soignant avec ce patient ; `SansRelationDeSoin` sinon."""
    cas, visites = await _cas_et_visites(fhir, patient)
    return relation.exiger_relation(cas, visites, soignant.etablissement)


async def _allergies(fhir: ClientFhir, patient: str) -> list[dict[str, Any]]:
    trouvees = await fhir.chercher("AllergyIntolerance", {"patient": f"Patient/{patient}"})
    return [fhir_soin.resume_allergie(a) for a in trouvees]


async def _groupe_sanguin(fhir: ClientFhir, patient: str) -> str | None:
    groupes = await fhir.chercher(
        "Observation", {"patient": f"Patient/{patient}", "code": f"{systemes.LOINC}|{fhir_soin.GROUPE_SANGUIN[0]}"}
    )
    return fhir_soin.valeur_du_groupe_sanguin(groupes)


async def _histoire(fhir: ClientFhir, patient: str) -> dict[str, list[dict[str, Any]]]:
    """Antécédents du patient et de sa famille, traitements au long cours en cours."""
    antecedents = await fhir.chercher(
        "Condition", {"patient": f"Patient/{patient}", "category": f"{systemes.CATEGORIE_DE_CONDITION}|problem-list-item"}
    )
    familiaux = await fhir.chercher("FamilyMemberHistory", {"patient": f"Patient/{patient}"})
    traitements = await fhir.chercher("MedicationStatement", {"subject": f"Patient/{patient}"})
    return {
        "antecedents": [
            fhir_soin.resume_antecedent(a)
            for a in sorted(antecedents, key=lambda a: a.get("recordedDate", ""), reverse=True)
            if fhir_soin.est_antecedent(a)
        ],
        "familiaux": [fhir_soin.resume_familial(f) for f in familiaux],
        "traitements": [fhir_soin.resume_traitement(t) for t in traitements if fhir_soin.traitement_actif(t)],
    }


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
            self._lus[cle] = fhir_soin.nom_de(await self._fhir.lire(type_, id_), id_)
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
                    "forme": fhir_soin.forme_du_produit(t["code"].get("text", "")),
                }
                for code, t in produits.items()
            ),
            key=lambda p: p["code"],
        ),
        "mesures": [{"code": m.code, "libelle": m.libelle, "unite": m.unite} for m in fhir_soin.MESURES.values()],
        "diagnostics": [{"code": d.code, "libelle": d.libelle} for d in fhir_soin.DIAGNOSTICS.values()],
        "allergies": [{"code_atc": code, "libelle": libelle} for code, libelle in fhir_soin.ALLERGIES.items()],
        "groupes_sanguins": list(fhir_soin.GROUPES_SANGUINS),
    }


async def rechercher(fhir: ClientFhir, soignant: Agent, npi: str) -> str:
    """L'identifiant du Patient qui porte ce NPI : le NPI n'entre qu'ici. Recherche tracée."""
    patient = await patient_par_npi(fhir, npi)
    if patient is None:
        raise PatientInconnu()
    await _tracer(fhir, soignant, patient["id"], "read", "recherche")
    return str(patient["id"])


async def bandeau(fhir: ClientFhir, soignant: Agent, patient_id: str) -> dict[str, Any]:
    """Ce qui reste à l'écran : identité, groupe sanguin, allergies, histoire et cas. Sans relation de
    soin, ni histoire ni motif des cas d'ailleurs : identité, allergies et groupe sanguin sauvent des vies."""
    patient = await _patient(fhir, patient_id)
    cas, visites = await _cas_et_visites(fhir, patient_id)
    motif = relation.motif_de_la_relation(cas, visites, soignant.etablissement)
    histoire = await _histoire(fhir, patient_id) if motif else {"antecedents": [], "familiaux": [], "traitements": []}
    noms = _Noms(fhir)
    resume_des_cas = []
    for c in sorted(cas, key=fhir_soin.debut, reverse=True):
        d_ici = fhir_soin.etablissement_du_cas(c) == soignant.etablissement
        resume_des_cas.append(
            {
                "id": c["id"],
                "motif": fhir_soin.motif_du_cas(c) if motif or d_ici else None,
                "statut": fhir_soin.statut_du_cas(c),
                "etablissement": await noms.de(c.get("managingOrganization")),
                "etablissement_id": fhir_soin.etablissement_du_cas(c),
                "de_mon_etablissement": relation.cas_de_l_etablissement(c, visites, soignant.etablissement),
                "debut": fhir_soin.debut(c) or None,
            }
        )
    resultat = {
        "patient": fhir_soin.resume_patient(patient),
        "groupe_sanguin": await _groupe_sanguin(fhir, patient_id),
        "allergies": await _allergies(fhir, patient_id),
        **histoire,
        "cas": resume_des_cas,
        "relation_de_soin": motif is not None,
    }
    await _tracer(fhir, soignant, patient_id, "read", motif or "recherche")
    return resultat


async def dossier(fhir: ClientFhir, soignant: Agent, patient_id: str) -> dict[str, Any]:
    """Tout le dossier, cas par cas, visite par visite. `SansRelationDeSoin` sinon. Lecture tracée."""
    patient = await _patient(fhir, patient_id)
    cas, visites = await _cas_et_visites(fhir, patient_id)
    motif = relation.exiger_relation(cas, visites, soignant.etablissement)
    parametres = {"patient": f"Patient/{patient_id}"}
    observations = await fhir.chercher("Observation", parametres)
    conditions = await fhir.chercher("Condition", parametres)
    lignes = await fhir.chercher("MedicationRequest", parametres)
    histoire = await _histoire(fhir, patient_id)
    await _tracer(fhir, soignant, patient_id, "read", motif)

    diagnostics = [c for c in conditions if not fhir_soin.est_antecedent(c)]
    par_visite: dict[str, dict[str, list[Ressource]]] = {}
    for genre, ressources in (("mesures", observations), ("diagnostics", diagnostics), ("lignes", lignes)):
        for r in ressources:
            if v := fhir_soin.visite_de(r):
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
            "urgence": fhir_soin.visite_d_urgence(v),
            "date": fhir_soin.debut(v) or None,
            "motif": fhir_soin.motif_de_la_visite(v),
            "etablissement": await noms.de(v.get("serviceProvider")),
            "soignant": await noms.de(fhir_soin.soignant_de_la_visite(v)),
            "mesures": [fhir_soin.resume_mesure(m) for m in contenu.get("mesures", [])],
            "diagnostics": [fhir_soin.resume_diagnostic(d) for d in contenu.get("diagnostics", [])],
            "ordonnance": {"numero": numero, "lignes": [fhir_soin.resume_ligne(l) for l in lignes_v]}
            if lignes_v
            else None,
        }

    resultat = []
    for c in sorted(cas, key=fhir_soin.debut, reverse=True):
        visites_du_cas = sorted((v for v in visites if c["id"] in fhir_soin.cas_de_la_visite(v)), key=fhir_soin.debut)
        resultat.append(
            {
                "id": c["id"],
                "motif": fhir_soin.motif_du_cas(c),
                "statut": fhir_soin.statut_du_cas(c),
                "etablissement": await noms.de(c.get("managingOrganization")),
                "debut": fhir_soin.debut(c) or None,
                "fin": fhir_soin.fin(c),
                "visites": [await une_visite(v) for v in visites_du_cas],
            }
        )
    resume = fhir_soin.resume_patient(patient)
    return {
        "patient": resume,
        "npi": resume["npi"],
        "groupe_sanguin": fhir_soin.valeur_du_groupe_sanguin(observations),
        "allergies": await _allergies(fhir, patient_id),
        **histoire,
        "cas": resultat,
        "mesures_series": fhir_soin.series_de_mesures(observations),
    }


async def ouvrir_cas(fhir: ClientFhir, soignant: Agent, patient_id: str, demande: modeles.NouveauCas) -> str:
    """Un nouveau cas à l'établissement du soignant : la relation de soin est établie. Tracé."""
    await _patient(fhir, patient_id)
    cas = avec_origine(
        fhir_soin.episode_of_care(
            patient=patient_id, etablissement=soignant.etablissement, soignant=soignant.sub, motif=demande.motif
        ),
        "visite",
    )
    await fhir.transaction([ecriture(cas)])
    await _tracer(fhir, soignant, patient_id, "create", "relation-de-soin", ressource=reference("EpisodeOfCare", cas["id"]))
    return str(cas["id"])


async def _cas_actif(fhir: ClientFhir, cas_id: str) -> tuple[Ressource, str]:
    """Le cas et l'identifiant de son patient ; `CasInconnu`, ou `CasClos` s'il ne l'est plus."""
    cas = await fhir.lire("EpisodeOfCare", cas_id)
    if cas is None:
        raise CasInconnu()
    if not fhir_soin.cas_actif(cas):
        raise CasClos()
    patient = fhir_soin.patient_du_cas(cas)
    if patient is None:
        raise CasInconnu()
    return cas, patient


async def enregistrer_visite(
    fhir: ClientFhir, soignant: Agent, cas_id: str, visite: modeles.NouvelleVisite
) -> tuple[str, str | None]:
    """Une visite dans un cas actif, d'ici ou d'ailleurs : la continuer établit la relation de soin.

    Tout part en une transaction : la visite, ses mesures, son diagnostic, les lignes de son
    ordonnance sous un seul numéro. `VisiteRefusee` quand un élément sort d'un catalogue.
    """
    cas, patient = await _cas_actif(fhir, cas_id)
    ordonnance = visite.ordonnance or []
    for m in visite.mesures:
        regles_visite.verifier_mesure(m.code, m.valeur, m.valeur2)
    if visite.diagnostic:
        regles_visite.verifier_diagnostic(visite.diagnostic.code)
    tarifs_ici = await tarifs(fhir, soignant.etablissement) if ordonnance else {}
    for l in ordonnance:
        regles_visite.verifier_ligne(l.produit, tarifs_ici, list(l.moments), l.jours, l.quantite)

    commun = {"patient": patient, "soignant": soignant.sub}
    rencontre = fhir_soin.encounter(
        cas=cas_id, etablissement=soignant.etablissement, type_=visite.type, motif=visite.motif, **commun
    )
    ressources = [rencontre]
    for m in visite.mesures:
        ressources.append(
            fhir_soin.observation(
                mesure=fhir_soin.MESURES[m.code], valeur=m.valeur, valeur2=m.valeur2, visite=rencontre["id"], **commun
            )
        )
    if visite.diagnostic:
        ressources.append(
            fhir_soin.condition(
                diagnostic=fhir_soin.DIAGNOSTICS[visite.diagnostic.code],
                confirme=regles_visite.diagnostic_confirme(soignant.role, visite.diagnostic.confirme),
                note=visite.diagnostic.note or None,
                visite=rencontre["id"],
                **commun,
            )
        )
    numero = numero_d_ordonnance() if ordonnance else None
    for l in ordonnance:
        ressources.append(
            fhir_soin.medication_request(
                tarif=tarifs_ici[l.produit],
                quantite=l.quantite,
                dose=l.dose,
                moments=list(l.moments),
                jours=l.jours,
                numero=numero or "",
                visite=rencontre["id"],
                etablissement=soignant.etablissement,
                **commun,
            )
        )
    await fhir.transaction([ecriture(avec_origine(r, "visite")) for r in ressources])
    _, visites = await _cas_et_visites(fhir, patient)
    motif: Motif = "acces-urgence" if relation.cas_d_urgence(cas, visites) else "relation-de-soin"
    await _tracer(fhir, soignant, patient, "create", motif, ressource=reference("Encounter", rencontre["id"]))
    return str(rencontre["id"]), numero


async def clore_cas(fhir: ClientFhir, soignant: Agent, cas_id: str) -> None:
    """Clôt un cas : il faut une relation de soin avec ce cas-là. Nouvelle version, tracée."""
    cas, patient = await _cas_actif(fhir, cas_id)
    tous, visites = await _cas_et_visites(fhir, patient)
    motif = relation.exiger_relation(tous, visites, soignant.etablissement, avec_le_cas=cas_id)
    await fhir.mettre_a_jour(fhir_soin.clore(cas))
    await _tracer(fhir, soignant, patient, "update", motif, ressource=reference("EpisodeOfCare", cas_id))


async def _ecrire_au_dossier(
    fhir: ClientFhir, soignant: Agent, patient_id: str, ressource: Ressource, document_id: str | None = None
) -> str:
    """Écrit `ressource` au dossier du patient, avec une relation de soin, marquée de son origine. Tracé.

    Avec `document_id`, l'entrée est reportée depuis ce Document, qui doit être du même patient : elle
    porte l'origine `report`, et un `Provenance` la lie à son Document (ADR 0007)."""
    await _patient(fhir, patient_id)
    motif = await _motif_exige(fhir, soignant, patient_id)
    if document_id:
        regles_documents.exiger_document_du_patient(await fhir.lire("DocumentReference", document_id), patient_id)
    ecrite = await fhir.creer(avec_origine(ressource, regles_documents.origine_de_la_saisie(document_id)))
    cible = reference(ressource["resourceType"], ecrite["id"])
    if document_id:
        await fhir.creer(fhir_documents.provenance_de_report(cible=cible, document=document_id, soignant=soignant.sub))
    await _tracer(fhir, soignant, patient_id, "create", motif, ressource=cible)
    return str(ecrite["id"])


async def declarer_allergie(
    fhir: ClientFhir, soignant: Agent, patient_id: str, demande: modeles.NouvelleAllergie
) -> str:
    libelle = regles_dossier.verifier_allergie(demande.code_atc)
    allergie = fhir_soin.allergy_intolerance(
        patient=patient_id, code_atc=demande.code_atc, libelle=libelle, soignant=soignant.sub
    )
    return await _ecrire_au_dossier(fhir, soignant, patient_id, allergie, demande.document_id)


async def ajouter_antecedent(
    fhir: ClientFhir, soignant: Agent, patient_id: str, demande: modeles.NouvelAntecedent
) -> str:
    """Un antécédent médical ou chirurgical du patient, ou familial. Jamais modifié : un correctif
    est une nouvelle entrée, l'ancienne marquée résolue."""
    regles_dossier.verifier_antecedent(demande.type, demande.lien)
    if demande.type == "familial":
        assert demande.lien is not None
        ressource = fhir_soin.family_member_history(patient=patient_id, lien=demande.lien, libelle=demande.libelle)
    else:
        ressource = fhir_soin.antecedent(
            patient=patient_id,
            type_=demande.type,
            libelle=demande.libelle,
            depuis=demande.depuis,
            actif=demande.actif,
            soignant=soignant.sub,
        )
    return await _ecrire_au_dossier(fhir, soignant, patient_id, ressource, demande.document_id)


async def ajouter_traitement(
    fhir: ClientFhir, soignant: Agent, patient_id: str, demande: modeles.NouveauTraitement
) -> str:
    """Un traitement au long cours : un produit du catalogue de l'établissement, ou un libellé libre."""
    tarif = (await tarifs(fhir, soignant.etablissement)).get(demande.produit) if demande.produit else None
    libelle = regles_dossier.libelle_du_traitement(
        demande.produit, tarif["code"].get("text", demande.produit) if tarif else None, demande.libelle
    )
    ressource = fhir_soin.medication_statement(
        patient=patient_id,
        tarif=tarif,
        libelle=libelle,
        posologie=demande.posologie,
        moments=list(demande.moments),
        soignant=soignant.sub,
    )
    return await _ecrire_au_dossier(fhir, soignant, patient_id, ressource)


async def arreter_traitement(fhir: ClientFhir, soignant: Agent, traitement_id: str) -> None:
    """Arrête un traitement au long cours : nouvelle version, avec une relation de soin. Tracé."""
    traitement = await fhir.lire("MedicationStatement", traitement_id)
    patient = fhir_soin.patient_du_traitement(traitement) if traitement else None
    if traitement is None or patient is None:
        raise TraitementInconnu()
    motif = await _motif_exige(fhir, soignant, patient)
    await fhir.mettre_a_jour(fhir_soin.arreter_traitement(traitement))
    await _tracer(fhir, soignant, patient, "update", motif, ressource=reference("MedicationStatement", traitement_id))


async def fixer_groupe_sanguin(
    fhir: ClientFhir, soignant: Agent, patient_id: str, demande: modeles.GroupeSanguin
) -> str:
    """Le groupe sanguin, relevé maintenant : le plus récent fait foi."""
    valeur = regles_dossier.groupe_sanguin(demande.valeur)
    await _ecrire_au_dossier(
        fhir, soignant, patient_id, fhir_soin.groupe_sanguin(patient=patient_id, valeur=valeur, soignant=soignant.sub)
    )
    return valeur


async def acces_d_urgence(
    fhir: ClientFhir, soignant: Agent, patient_id: str, demande: modeles.DemandeDUrgence
) -> tuple[str, str]:
    """Accès d'urgence : un cas neuf et sa visite EMER à l'établissement du soignant, tracés avec
    le motif `acces-urgence` et la raison déclarée. La relation de soin tient ensuite par ce cas."""
    await _patient(fhir, patient_id)
    cas = fhir_soin.episode_of_care(
        patient=patient_id, etablissement=soignant.etablissement, soignant=soignant.sub, motif="Accès d'urgence"
    )
    rencontre = fhir_soin.encounter(
        patient=patient_id,
        cas=cas["id"],
        etablissement=soignant.etablissement,
        soignant=soignant.sub,
        type_="urgence",
        motif=demande.raison,
    )
    await fhir.transaction([ecriture(avec_origine(cas, "visite")), ecriture(avec_origine(rencontre, "visite"))])
    await _tracer(
        fhir, soignant, patient_id, "create", "acces-urgence", raison=demande.raison,
        ressource=reference("Encounter", rencontre["id"]),
    )
    return str(cas["id"]), str(rencontre["id"])


async def documents(fhir: ClientFhir, soignant: Agent, patient_id: str) -> list[fhir_documents.DocumentVu]:
    """Les Documents du patient, du plus récent au plus ancien, avec une relation de soin. Lecture tracée."""
    await _patient(fhir, patient_id)
    motif = await _motif_exige(fhir, soignant, patient_id)
    trouves = await fhir_documents.documents_du_patient(fhir, patient_id)
    relues = await fhir_transcriptions.transcriptions_relues_du_patient(fhir, patient_id)
    await _tracer(fhir, soignant, patient_id, "read", motif)
    return [fhir_documents.document_vu(d, transcription=d["id"] in relues) for d in trouves]


async def _document_lisible(fhir: ClientFhir, soignant: Agent, document_id: str) -> tuple[Ressource, str, Motif]:
    """Le Document, son patient, et le motif de la relation de soin du soignant avec lui."""
    document = await fhir.lire("DocumentReference", document_id)
    patient = id_de(document.get("subject")) if document else None
    if document is None or patient is None:
        raise DocumentInconnu()
    return document, patient, await _motif_exige(fhir, soignant, patient)


async def transcription_du_document(
    fhir: ClientFhir, soignant: Agent, document_id: str
) -> fhir_transcriptions.TranscriptionLue:
    """La Transcription relue d'un Document, avec une relation de soin avec son patient. Lecture tracée.
    Une version préliminaire, en relecture, n'en est pas une : `TranscriptionInconnue`."""
    document, patient, motif = await _document_lisible(fhir, soignant, document_id)
    relue = await fhir_transcriptions.transcription_relue(fhir, document_id)
    lue = await fhir_transcriptions.lire_transcription(fhir, document, relue) if relue else None
    if lue is None:
        raise TranscriptionInconnue()
    await _tracer(fhir, soignant, patient, "read", motif, ressource=reference("DocumentReference", relue["id"]))
    return lue


async def page_du_document(fhir: ClientFhir, soignant: Agent, document_id: str, rang: int) -> Page:
    """La page `rang` d'un Document, avec une relation de soin avec son patient. Lecture tracée."""
    document = await fhir.lire("DocumentReference", document_id)
    patient = id_de(document.get("subject")) if document else None
    if document is None or patient is None:
        raise DocumentInconnu()
    motif = await _motif_exige(fhir, soignant, patient)
    lue = await fhir_documents.page(fhir, document, rang)
    if lue is None:
        raise PageInconnue()
    await _tracer(fhir, soignant, patient, "read", motif, ressource=reference("DocumentReference", document_id))
    return lue


async def ajouter_document(
    fhir: ClientFhir,
    soignant: Agent,
    patient_id: str,
    *,
    type_: str,
    annee: str,
    lisibilite: str,
    etablissement: str | None,
    pages: list[Page],
    papier_abime: str | None = None,
) -> dict[str, Any]:
    """Un Document que le patient a apporté, numérisé pendant la visite : origine `numerisation`,
    auteur le soignant. Avec une relation de soin. Tracé. `commun.fhir.documents.valider_document` le juge,
    comme au guichet de numérisation, avant toute écriture."""
    await _patient(fhir, patient_id)
    motif = await _motif_exige(fhir, soignant, patient_id)
    ecrit = await fhir_documents.ecrire_document(
        fhir,
        patient=patient_id,
        auteur=soignant.sub,
        type_=type_,
        annee=annee,
        pages=pages,
        lisibilite=lisibilite,
        etablissement_d_origine=etablissement,
        papier_abime=papier_abime,
    )
    await _tracer(fhir, soignant, patient_id, "create", motif, ressource=reference("DocumentReference", ecrit["id"]))
    return {"document_id": ecrit["id"], "pages": len(pages)}
