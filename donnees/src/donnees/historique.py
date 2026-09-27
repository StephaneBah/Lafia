"""Histoire clinique de démonstration (F3.6, F4.4) : de quoi montrer un carnet vécu, une caisse et une pharmacie.

Les ressources suivent le contrat FHIR de docs/specs/F3-v1-complete.md et de
docs/specs/F4-dossier-approfondi.md. Leurs identifiants sont fixes
(`hist-…`) : rejouer le chargement les remet dans l'état du jeu, en nouvelle version. Leurs dates sont
relatives à l'instant du chargement, pour qu'un traitement soit toujours en cours le jour de la démo.

Les numéros à montrer (citoyens de citoyens.toml, patients de patients.toml) :

- patient-001, NPI 0000001204815, code carnet H3T-9QR : le carnet vécu.
  - Cas terminé, il y a deux mois, CHUZ Abomey-Calavi : paludisme confirmé (TDR positif, 39,4 °C),
    ordonnance ORD-5PW-8RB payée (REC-6DK-2MV) et toute remise.
  - Cas en cours, il y a trois jours, CNHU-HKM : fièvre et toux, IRA provisoire, ordonnance
    ORD-7K4-M2P payée (REC-4TB-6WN) : paracétamol remis, amoxicilline remise en partie (7 sur 14) ;
    traitement en cours aujourd'hui.
  - Allergie AINS (ATC M01A). Groupe sanguin O+. Antécédents : hypertension depuis 2019 (active),
    appendicectomie en 2015, mère diabétique ; traitement au long cours : amlodipine 5 mg le matin.
    Journal d'accès : soignants, caisse, pharmacie, et un accès d'urgence
    au CHUD Borgou-Alibori, avec son motif.
  - Un ancien carnet papier numérisé (4 pages, 2015-2019), relu et contrôlé : sa Transcription (ADR 0010)
    en quatre volets, au CS Kpanroun et au CHD Ouémé, qu'on lit dans soin et dans « Par établissement ».
- patient-007, NPI 0000001763547, code carnet W6N-2JD : cas en cours d'hier au CNHU-HKM, ordonnance
  ORD-3HX-9KT non payée, avec de l'ibuprofène alors qu'une allergie AINS est connue : la caisse encaisse,
  la pharmacie est arrêtée par l'allergie. Groupe sanguin A+, asthme depuis l'enfance.
- patient-013, NPI 0000002316294, code carnet B8F-5ZE : rien de clinique, le carnet vide.
"""

import base64
import struct
import zlib
from datetime import datetime, timedelta, timezone
from typing import Any

import donnees
from commun.fhir import systemes
from commun.fhir.documents import Page, avec_origine, binary, document_reference
from commun.fhir.client import Ressource
from commun.fhir.ressources import DEVISE

SNOMED = "http://snomed.info/sct"
CATEGORIE_D_OBSERVATION = "http://terminology.hl7.org/CodeSystem/observation-category"
CLASSE_DE_VISITE = "http://terminology.hl7.org/CodeSystem/v3-ActCode"
STATUT_CLINIQUE = "http://terminology.hl7.org/CodeSystem/condition-clinical"
MOMENTS_FHIR = {"matin": "MORN", "midi": "NOON", "soir": "EVE", "nuit": "NIGHT"}
# ADR 0010 : une Transcription est du Markdown ; l'issue d'une Tâche de relecture se dit dans ce système.
FORMAT_DE_TRANSCRIPTION = "text/markdown; charset=utf-8"
ISSUE_DE_RELECTURE = f"{systemes.LAFIA}/CodeSystem/issue-de-relecture"


def _ref(type_: str, id_: str) -> dict[str, str]:
    return {"reference": f"{type_}/{id_}"}


def _instant(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds")


class _Histoire:
    """Écrit les ressources d'un patient, datées par rapport à `maintenant`."""

    def __init__(self, maintenant: datetime) -> None:
        self.maintenant = maintenant.replace(microsecond=0)
        self.ressources: list[Ressource] = []
        self._tarifs = {(t.etablissement, t.produit.code): t for t in donnees.tarifs()}

    def il_y_a(self, jours: float, heure: int = 9, minute: int = 0) -> datetime:
        """Il y a `jours` jours, à `heure`:`minute` heure du Bénin (UTC+1)."""
        jour = (self.maintenant - timedelta(days=jours)).astimezone(timezone(timedelta(hours=1)))
        return jour.replace(hour=heure, minute=minute, second=0)

    def _ajouter(self, ressource: Ressource) -> Ressource:
        self.ressources.append(ressource)
        return ressource

    def cas(self, id_: str, patient: str, etablissement: str, soignant: str, motif: str,
            debut: datetime, fin: datetime | None = None) -> None:
        periode = {"start": _instant(debut)}
        if fin:
            periode["end"] = _instant(fin)
        self._ajouter({
            "resourceType": "EpisodeOfCare", "id": id_,
            "status": "finished" if fin else "active",
            "type": [{"text": motif}],
            "patient": _ref("Patient", patient),
            "managingOrganization": _ref("Organization", etablissement),
            "careManager": _ref("Practitioner", soignant),
            "period": periode,
        })

    def visite(self, id_: str, patient: str, cas: str, etablissement: str, soignant: str,
               type_: str, motif: str, debut: datetime) -> None:
        self._ajouter({
            "resourceType": "Encounter", "id": id_, "status": "finished",
            "class": {"system": CLASSE_DE_VISITE, "code": "EMER" if type_ == "urgence" else "AMB"},
            "type": [{"coding": [{"system": systemes.TYPE_DE_VISITE, "code": type_}]}],
            "subject": _ref("Patient", patient),
            "episodeOfCare": [_ref("EpisodeOfCare", cas)],
            "participant": [{"individual": _ref("Practitioner", soignant)}],
            "serviceProvider": _ref("Organization", etablissement),
            "period": {"start": _instant(debut)},
            "reasonCode": [{"text": motif}],
        })

    def _mesure(self, id_: str, patient: str, visite: str, soignant: str, quand: datetime,
                categorie: str, loinc: str, libelle: str, **valeur: Any) -> None:
        self._ajouter({
            "resourceType": "Observation", "id": id_, "status": "final",
            "category": [{"coding": [{"system": CATEGORIE_D_OBSERVATION, "code": categorie}]}],
            "code": {"coding": [{"system": systemes.LOINC, "code": loinc}], "text": libelle},
            "subject": _ref("Patient", patient),
            "encounter": _ref("Encounter", visite),
            "effectiveDateTime": _instant(quand),
            "performer": [_ref("Practitioner", soignant)],
            **valeur,
        })

    def quantite(self, id_: str, patient: str, visite: str, soignant: str, quand: datetime,
                 loinc: str, libelle: str, valeur: float, unite: str, affichage: str) -> None:
        self._mesure(id_, patient, visite, soignant, quand, "vital-signs", loinc, libelle,
                     valueQuantity={"value": valeur, "unit": affichage, "system": systemes.UCUM, "code": unite})

    def tension(self, id_: str, patient: str, visite: str, soignant: str, quand: datetime,
                systolique: int, diastolique: int) -> None:
        def composante(loinc: str, valeur: int) -> dict[str, Any]:
            return {"code": {"coding": [{"system": systemes.LOINC, "code": loinc}]},
                    "valueQuantity": {"value": valeur, "unit": "mmHg", "system": systemes.UCUM, "code": "mm[Hg]"}}
        self._mesure(id_, patient, visite, soignant, quand, "vital-signs", "85354-9", "Tension artérielle",
                     component=[composante("8480-6", systolique), composante("8462-4", diastolique)])

    def tdr(self, id_: str, patient: str, visite: str, soignant: str, quand: datetime, positif: bool) -> None:
        resultat = {"coding": [{"system": SNOMED, "code": "10828004" if positif else "260385009"}],
                    "text": "positif" if positif else "négatif"}
        self._mesure(id_, patient, visite, soignant, quand, "laboratory", "70569-9", "TDR paludisme",
                     valueCodeableConcept=resultat)

    def diagnostic(self, id_: str, patient: str, visite: str, soignant: str, code: str, cim10: str,
                   libelle: str, confirme: bool, gueri: bool, note: str) -> None:
        self._ajouter({
            "resourceType": "Condition", "id": id_,
            "clinicalStatus": {"coding": [{"system": STATUT_CLINIQUE, "code": "resolved" if gueri else "active"}]},
            "category": [{"coding": [{"system": systemes.CATEGORIE_DE_CONDITION, "code": "encounter-diagnosis"}]}],
            "verificationStatus": {"coding": [{"system": systemes.VERIFICATION,
                                               "code": "confirmed" if confirme else "provisional"}]},
            "code": {"coding": [{"system": systemes.DIAGNOSTIC, "code": code, "display": libelle},
                                {"system": systemes.CIM_10, "code": cim10}], "text": libelle},
            "note": [{"text": note}],
            "subject": _ref("Patient", patient),
            "encounter": _ref("Encounter", visite),
            "recorder": _ref("Practitioner", soignant),
        })

    def antecedent(self, id_: str, patient: str, soignant: str, type_: str, libelle: str, depuis: str,
                   actif: bool, quand: datetime) -> None:
        """Un antécédent médical ou chirurgical : une Condition de la liste des problèmes, sans visite."""
        self._ajouter({
            "resourceType": "Condition", "id": id_,
            "category": [{"coding": [{"system": systemes.CATEGORIE_DE_CONDITION, "code": "problem-list-item"}]},
                         {"coding": [{"system": systemes.TYPE_D_ANTECEDENT, "code": type_}]}],
            "clinicalStatus": {"coding": [{"system": STATUT_CLINIQUE, "code": "active" if actif else "resolved"}]},
            "code": {"text": libelle},
            "onsetString": depuis,
            "subject": _ref("Patient", patient),
            "recorder": _ref("Practitioner", soignant),
            "recordedDate": _instant(quand),
        })

    def familial(self, id_: str, patient: str, lien: str, lien_en_mots: str, libelle: str, quand: datetime) -> None:
        """Un antécédent familial : la maladie d'un parent, par son lien au patient (v3 RoleCode)."""
        self._ajouter({
            "resourceType": "FamilyMemberHistory", "id": id_, "status": "completed",
            "patient": _ref("Patient", patient),
            "date": _instant(quand),
            "relationship": {"coding": [{"system": systemes.LIEN_DE_PARENTE, "code": lien}], "text": lien_en_mots},
            "condition": [{"code": {"text": libelle}}],
        })

    def traitement_au_long_cours(self, id_: str, patient: str, soignant: str, produit: str, posologie: str,
                                 moments: list[str], debut: datetime) -> None:
        """Un traitement au long cours : codé au catalogue quand le produit y est, toujours en texte."""
        connu = next((t.produit for (_, code), t in self._tarifs.items() if code == produit), None)
        medicament: dict[str, Any] = {"text": connu.libelle if connu else produit}
        if connu:
            medicament["coding"] = [{"system": systemes.CATALOGUE, "code": produit, "display": connu.libelle}]
            if connu.atc:
                medicament["coding"].append({"system": systemes.ATC, "code": connu.atc})
        self._ajouter({
            "resourceType": "MedicationStatement", "id": id_, "status": "active",
            "subject": _ref("Patient", patient),
            "medicationCodeableConcept": medicament,
            "effectivePeriod": {"start": _instant(debut)},
            "dateAsserted": _instant(debut),
            "informationSource": _ref("Practitioner", soignant),
            "dosage": [{"text": posologie, "timing": {"repeat": {"when": [MOMENTS_FHIR[m] for m in moments]}}}],
        })

    def groupe_sanguin(self, id_: str, patient: str, soignant: str, valeur: str, quand: datetime) -> None:
        self._ajouter({
            "resourceType": "Observation", "id": id_, "status": "final",
            "category": [{"coding": [{"system": CATEGORIE_D_OBSERVATION, "code": "laboratory"}]}],
            "code": {"coding": [{"system": systemes.LOINC, "code": "882-1"}], "text": "Groupe sanguin"},
            "subject": _ref("Patient", patient),
            "effectiveDateTime": _instant(quand),
            "performer": [_ref("Practitioner", soignant)],
            "valueCodeableConcept": {"text": valeur},
        })

    def allergie(self, id_: str, patient: str, soignant: str) -> None:
        self._ajouter({
            "resourceType": "AllergyIntolerance", "id": id_,
            "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical",
                                           "code": "active"}]},
            "code": {"coding": [{"system": systemes.ATC, "code": "M01A"}],
                     "text": "AINS (anti-inflammatoires : ibuprofène, diclofénac)"},
            "patient": _ref("Patient", patient),
            "recorder": _ref("Practitioner", soignant),
        })

    def ligne(self, id_: str, numero: str, patient: str, visite: str, soignant: str, etablissement: str,
              quand: datetime, produit: str, moments: list[str], par_prise: int, jours: int) -> None:
        tarif = self._tarifs[(etablissement, produit)]
        quantite = par_prise * len(moments) * jours
        codes = [{"system": systemes.CATALOGUE, "code": produit, "display": tarif.produit.libelle}]
        if tarif.produit.atc:
            codes.append({"system": systemes.ATC, "code": tarif.produit.atc})
        unite = "gélule" if "gélule" in tarif.produit.libelle else "comprimé"
        self._ajouter({
            "resourceType": "MedicationRequest", "id": id_, "status": "active", "intent": "order",
            "identifier": [{"system": systemes.ORDONNANCE, "value": numero}],
            "groupIdentifier": {"system": systemes.ORDONNANCE, "value": numero},
            "medicationCodeableConcept": {"coding": codes, "text": tarif.produit.libelle},
            "subject": _ref("Patient", patient),
            "encounter": _ref("Encounter", visite),
            "requester": _ref("Practitioner", soignant),
            "authoredOn": _instant(quand),
            "dispenseRequest": {"performer": _ref("Organization", etablissement),
                                "quantity": {"value": quantite, "unit": unite}},
            "dosageInstruction": [{
                "text": f"{par_prise} {unite}{'s' if par_prise > 1 else ''} {', '.join(moments)}, {jours} jours",
                "timing": {"repeat": {"when": [MOMENTS_FHIR[m] for m in moments],
                                      "boundsDuration": {"value": jours, "unit": "d",
                                                         "system": systemes.UCUM, "code": "d"}}},
                "doseAndRate": [{"doseQuantity": {"value": par_prise, "unit": unite}}],
            }],
        })

    def encaissement(self, id_: str, recepisse: str, numero: str, patient: str, etablissement: str,
                     caissier: str, quand: datetime, lignes: list[str]) -> None:
        prescrites = {r["id"]: r for r in self.ressources if r["resourceType"] == "MedicationRequest"}
        postes, total = [], 0
        for ligne in lignes:
            requete = prescrites[ligne]
            code = requete["medicationCodeableConcept"]["coding"][0]["code"]
            montant = self._tarifs[(etablissement, code)].prix * requete["dispenseRequest"]["quantity"]["value"]
            total += montant
            postes.append({
                "chargeItemCodeableConcept": {"coding": [{"system": systemes.LIGNE, "code": ligne}]},
                "priceComponent": [{"type": "base", "amount": {"value": montant, "currency": DEVISE}}],
            })
        self._ajouter({
            "resourceType": "Invoice", "id": id_, "status": "balanced",
            "identifier": [{"system": systemes.RECEPISSE, "value": recepisse},
                           {"system": systemes.ORDONNANCE, "value": numero}],
            "subject": _ref("Patient", patient),
            "issuer": _ref("Organization", etablissement),
            "participant": [{"actor": _ref("Practitioner", caissier)}],
            "date": _instant(quand),
            "lineItem": postes,
            "totalGross": {"value": total, "currency": DEVISE},
        })

    def delivrance(self, id_: str, ligne: str, patient: str, pharmacien: str, etablissement: str,
                   quand: datetime, quantite: int) -> None:
        requete = next(r for r in self.ressources if r["id"] == ligne)
        self._ajouter({
            "resourceType": "MedicationDispense", "id": id_, "status": "completed",
            "authorizingPrescription": [_ref("MedicationRequest", ligne)],
            "medicationCodeableConcept": requete["medicationCodeableConcept"],
            "subject": _ref("Patient", patient),
            "quantity": {"value": quantite, "unit": requete["dispenseRequest"]["quantity"]["unit"]},
            "performer": [{"actor": _ref("Practitioner", pharmacien)}, {"actor": _ref("Organization", etablissement)}],
            "whenHandedOver": _instant(quand),
        })

    def acces(self, id_: str, patient: str, quand: datetime, qui: str, etablissement: str, service: str,
              motif: str, action: str = "read", raison: str | None = None) -> None:
        usage: dict[str, Any] = {"coding": [{"system": systemes.MOTIF_D_ACCES, "code": motif}]}
        if raison:
            usage["text"] = raison
        self._ajouter({
            "resourceType": "AuditEvent", "id": id_,
            "type": {"system": systemes.DICOM, "code": "110110", "display": "Patient Record"},
            "subtype": [{"system": systemes.ACTION_REST, "code": action}],
            "action": {"read": "R", "create": "C", "update": "U"}[action],
            "recorded": _instant(quand),
            "outcome": "0",
            "agent": [{"who": _ref("Practitioner", qui), "requestor": True, "purposeOfUse": [usage]}],
            "source": {"site": service, "observer": _ref("Organization", etablissement)},
            "entity": [{"what": _ref("Patient", patient)}],
        })

    def document_transcrit(self, id_: str, patient: str, *, numerise: datetime, relu: datetime,
                           agent: str, relecteur: str, controleur: str, markdown: str,
                           pages: list[bytes], **document: Any) -> None:
        """Un Document numérisé, ses pages, et sa Transcription relue (ADR 0010) : le Markdown dans un
        Binary, la version finale qui `transforms` le scan, la Relecture et le Contrôle en Provenance, et
        la Tâche de relecture close, pour que la relecture ne la redonne à personne."""
        pages_ecrites = []
        for rang, octets in enumerate(pages, start=1):
            page = Page(format="image/png", octets=octets)
            self._ajouter({**binary(page, patient), "id": f"{id_}-page-{rang}"})
            pages_ecrites.append((f"{id_}-page-{rang}", page))
        scan = document_reference(patient=patient, auteur=agent, pages=pages_ecrites, depot=None, **document)
        self._ajouter({**scan, "id": id_, "date": _instant(numerise)})

        transcription = f"{id_}-transcription"
        self._ajouter({
            "resourceType": "Binary", "id": f"{transcription}-texte",
            "contentType": FORMAT_DE_TRANSCRIPTION,
            "securityContext": _ref("Patient", patient),
            "data": base64.b64encode(markdown.encode()).decode(),
        })
        self._ajouter(avec_origine({
            "resourceType": "DocumentReference", "id": transcription,
            "status": "current", "docStatus": "final",
            "type": {"coding": [{"system": systemes.TYPE_DE_DOCUMENT, "code": "transcription",
                                 "display": "Transcription"}], "text": "Transcription"},
            "subject": _ref("Patient", patient),
            "date": _instant(relu),
            "author": [_ref("Practitioner", relecteur), _ref("Practitioner", controleur)],
            "relatesTo": [{"code": "transforms", "target": _ref("DocumentReference", id_)}],
            "context": {"period": {"start": document["annee"]}},
            "content": [{"attachment": {"contentType": FORMAT_DE_TRANSCRIPTION, "url": f"Binary/{transcription}-texte",
                                        "size": len(markdown.encode()), "title": "Transcription"}}],
        }, "extraction"))
        for activite, libelle, qui, role, quand in (
            ("relecture", "Relecture", relecteur, "Relu par", relu - timedelta(days=2)),
            ("controle", "Contrôle", controleur, "Contrôlé par", relu),
        ):
            self._ajouter({
                "resourceType": "Provenance", "id": f"{transcription}-{activite}",
                "target": [_ref("DocumentReference", transcription)],
                "recorded": _instant(quand),
                "activity": {"coding": [{"system": systemes.RELECTURE, "code": activite, "display": libelle}],
                             "text": libelle},
                "agent": [{"type": {"text": role}, "who": _ref("Practitioner", qui)}],
                "entity": [{"role": "source", "what": _ref("DocumentReference", id_)}],
            })
        annee, numero, _ = relu.isocalendar()
        self._ajouter({
            "resourceType": "Task", "id": f"{id_}-relecture",
            "meta": {"tag": [{"system": systemes.SEMAINE_DE_RELECTURE, "code": f"{annee}-W{numero:02d}"}]},
            "status": "completed", "intent": "order",
            "code": {"coding": [{"system": systemes.RELECTURE, "code": "relecture", "display": "Relecture"}]},
            "businessStatus": {"coding": [{"system": ISSUE_DE_RELECTURE, "code": "relue", "display": "Relue"}]},
            "focus": _ref("DocumentReference", id_),
            "for": _ref("Patient", patient),
            "owner": _ref("Practitioner", relecteur),
            "authoredOn": _instant(numerise),
            "executionPeriod": {"start": _instant(numerise), "end": _instant(relu)},
            "output": [{"type": {"text": "Transcription"},
                        "valueReference": _ref("DocumentReference", transcription)}],
        })


def _patient_a(h: _Histoire) -> None:
    """patient-001 : un cas terminé, un cas en cours, une allergie, un journal d'accès."""
    p = "patient-001"
    # Cas terminé : paludisme, il y a deux mois, au CHUZ Abomey-Calavi.
    calavi, medecin, infirmier, caissier, pharmacien = (
        "chuz-abomey-calavi", "agent-15", "agent-16", "agent-17", "agent-18")
    debut, controle = h.il_y_a(60, 10, 12), h.il_y_a(53, 9, 40)
    h.cas("hist-a-cas-palu", p, calavi, medecin, "Fièvre et frissons", debut, fin=controle)
    h.visite("hist-a-visite-palu-1", p, "hist-a-cas-palu", calavi, medecin, "consultation",
             "Fièvre depuis deux jours, frissons", debut)
    h.quantite("hist-a-mesure-palu-temp", p, "hist-a-visite-palu-1", infirmier, debut,
               "8310-5", "Température", 39.4, "Cel", "°C")
    h.tdr("hist-a-mesure-palu-tdr", p, "hist-a-visite-palu-1", infirmier, debut, positif=True)
    h.diagnostic("hist-a-diag-palu", p, "hist-a-visite-palu-1", medecin, "paludisme", "B54",
                 "Paludisme", confirme=True, gueri=True, note="Paludisme simple, TDR positif.")
    h.ligne("hist-a-ligne-palu-artemether", "ORD-5PW-8RB", p, "hist-a-visite-palu-1", medecin, calavi,
            debut, "MED-ARTEMETHER-LUMEF", ["matin", "soir"], 1, 3)
    h.ligne("hist-a-ligne-palu-paracetamol", "ORD-5PW-8RB", p, "hist-a-visite-palu-1", medecin, calavi,
            debut, "MED-PARACETAMOL-500", ["matin", "midi", "soir"], 1, 3)
    paye = h.il_y_a(60, 10, 40)
    h.encaissement("hist-a-encaissement-palu", "REC-6DK-2MV", "ORD-5PW-8RB", p, calavi, caissier, paye,
                   ["hist-a-ligne-palu-artemether", "hist-a-ligne-palu-paracetamol"])
    remis = h.il_y_a(60, 10, 55)
    h.delivrance("hist-a-delivrance-palu-artemether", "hist-a-ligne-palu-artemether", p, pharmacien, calavi, remis, 6)
    h.delivrance("hist-a-delivrance-palu-paracetamol", "hist-a-ligne-palu-paracetamol", p, pharmacien, calavi, remis, 9)
    h.visite("hist-a-visite-palu-2", p, "hist-a-cas-palu", calavi, infirmier, "continuite",
             "Visite de contrôle", controle)
    h.quantite("hist-a-mesure-palu-temp-2", p, "hist-a-visite-palu-2", infirmier, controle,
               "8310-5", "Température", 36.8, "Cel", "°C")
    h.acces("hist-a-acces-palu-1", p, debut, medecin, calavi, "soin", "relation-de-soin", "create")
    h.acces("hist-a-acces-palu-2", p, paye, caissier, calavi, "caisse", "numero-d-ordonnance")
    h.acces("hist-a-acces-palu-3", p, remis, pharmacien, calavi, "pharmacie", "numero-d-ordonnance")
    h.acces("hist-a-acces-palu-4", p, controle, infirmier, calavi, "soin", "relation-de-soin", "update")

    # Allergie connue depuis ce premier cas, et ce qui dure au-delà des cas, dit ce jour-là.
    h.allergie("hist-a-allergie-ains", p, medecin)
    h.groupe_sanguin("hist-a-groupe-sanguin", p, medecin, "O+", debut)
    h.antecedent("hist-a-antecedent-hta", p, medecin, "medical", "Hypertension artérielle", "2019", True, debut)
    h.antecedent("hist-a-antecedent-appendicectomie", p, medecin, "chirurgical", "Appendicectomie", "2015", False, debut)
    h.familial("hist-a-familial-mere-diabete", p, "MTH", "Mère", "Diabète", debut)
    h.traitement_au_long_cours("hist-a-traitement-amlodipine", p, medecin, "MED-AMLODIPINE-5",
                               "1 comprimé le matin", ["matin"], h.il_y_a(6 * 365))

    # Accès d'urgence, il y a trois semaines, au CHUD Borgou-Alibori.
    h.acces("hist-a-acces-urgence", p, h.il_y_a(21, 19, 48), "agent-11", "chud-borgou-alibori", "soin",
            "acces-urgence", raison="Patient inconscient après un accident de moto, amené par les pompiers.")

    # Un ancien carnet papier, déposé au CNHU-HKM il y a trois semaines, relu hors du Littoral puis contrôlé.
    h.document_transcrit(
        "hist-a-carnet-papier", p,
        numerise=h.il_y_a(24, 11, 5), relu=h.il_y_a(10, 16, 20),
        agent="agent-23", relecteur="agent-25", controleur="agent-26",
        markdown=CARNET_PAPIER_TRANSCRIT, pages=[_page_de_carnet(n) for n in range(1, 5)],
        type_="carnet", annee="2015", lisibilite="partiel", etablissement_d_origine="CS Kpanroun",
        papier_abime="Coin inférieur de la page 3 déchiré avant le dépôt : la fin du tableau manque.",
    )

    # Cas en cours : fièvre et toux, il y a trois jours, au CNHU-HKM.
    cnhu, medecin, infirmier, caissier, pharmacien = "cnhu-hkm", "agent-01", "agent-03", "agent-04", "agent-05"
    visite = h.il_y_a(3, 10, 30)
    h.cas("hist-a-cas-ira", p, cnhu, medecin, "Fièvre et toux", visite)
    h.visite("hist-a-visite-ira-1", p, "hist-a-cas-ira", cnhu, medecin, "consultation",
             "Fièvre et toux depuis quatre jours", visite)
    h.quantite("hist-a-mesure-ira-temp", p, "hist-a-visite-ira-1", infirmier, visite,
               "8310-5", "Température", 38.6, "Cel", "°C")
    h.quantite("hist-a-mesure-ira-pouls", p, "hist-a-visite-ira-1", infirmier, visite,
               "8867-4", "Pouls", 96, "/min", "battements par minute")
    h.tension("hist-a-mesure-ira-tension", p, "hist-a-visite-ira-1", infirmier, visite, 120, 80)
    h.quantite("hist-a-mesure-ira-poids", p, "hist-a-visite-ira-1", infirmier, visite,
               "29463-7", "Poids", 74, "kg", "kg")
    h.tdr("hist-a-mesure-ira-tdr", p, "hist-a-visite-ira-1", infirmier, visite, positif=False)
    h.diagnostic("hist-a-diag-ira", p, "hist-a-visite-ira-1", medecin, "ira", "J06.9",
                 "Infection respiratoire aiguë", confirme=False, gueri=False,
                 note="Toux grasse, gorge rouge. Revenir si la fièvre dure plus de trois jours.")
    h.ligne("hist-a-ligne-ira-paracetamol", "ORD-7K4-M2P", p, "hist-a-visite-ira-1", medecin, cnhu,
            visite, "MED-PARACETAMOL-500", ["matin", "midi", "soir"], 1, 5)
    h.ligne("hist-a-ligne-ira-amoxicilline", "ORD-7K4-M2P", p, "hist-a-visite-ira-1", medecin, cnhu,
            visite, "MED-AMOXICILLINE-500", ["matin", "soir"], 1, 7)
    paye = h.il_y_a(3, 11, 5)
    h.encaissement("hist-a-encaissement-ira", "REC-4TB-6WN", "ORD-7K4-M2P", p, cnhu, caissier, paye,
                   ["hist-a-ligne-ira-paracetamol", "hist-a-ligne-ira-amoxicilline"])
    remis = h.il_y_a(3, 11, 20)
    h.delivrance("hist-a-delivrance-ira-paracetamol", "hist-a-ligne-ira-paracetamol", p, pharmacien, cnhu, remis, 15)
    h.delivrance("hist-a-delivrance-ira-amoxicilline", "hist-a-ligne-ira-amoxicilline", p, pharmacien, cnhu, remis, 7)
    h.acces("hist-a-acces-ira-1", p, visite, medecin, cnhu, "soin", "relation-de-soin", "create")
    h.acces("hist-a-acces-ira-2", p, paye, caissier, cnhu, "caisse", "numero-d-ordonnance")
    h.acces("hist-a-acces-ira-3", p, remis, pharmacien, cnhu, "pharmacie", "numero-d-ordonnance")


# Le carnet papier de patient-001, tel que les agents de relecture l'ont recopié (ADR 0010) : l'appendicectomie
# de 2015 et l'hypertension de 2019 que son dossier connaît déjà.
CARNET_PAPIER_TRANSCRIT = """---
etablissements: CS Kpanroun; CHD Ouémé
periode: 2015-2019
---

## consultation · 2015-06-02 · CS Kpanroun · p. 1
Motif : douleurs du ventre à droite depuis la veille, vomissements.
T° 38,4. Défense en fosse iliaque droite.
Conclusion : **suspicion d'appendicite** ; orientée au CHD Ouémé.

![Tampon et signature du centre](page:1)

## hospitalisation · 2015-06-03 · CHD Ouémé · p. 2
Entrée en chirurgie le 3 juin 2015.
- Appendicectomie le jour même, sous anesthésie générale.
- Suites simples ; sortie le 6 juin.

*Contrôle à quinze jours au centre de santé.*

## analyse · 2015-06-03 · CHD Ouémé · p. 3
| Examen | Résultat | Unité |
|---|---|---|
| Globules blancs | 14 200 | /mm³ |
| Hémoglobine | 12,1 | g/dL |
| Goutte épaisse | négative | |

![Feuille de résultats, haut de la page](page:3#0,0,1000,450)

## consultation · 2019-03-14 · CS Kpanroun · p. 4
Motif : maux de tête.
TA 160/95 à deux reprises.
Conclusion : hypertension artérielle ; amlodipine 5 mg le matin, revoir dans un mois.
"""


def _page_de_carnet(numero: int, largeur: int = 120, hauteur: int = 170) -> bytes:
    """Une page de carnet de démonstration : un PNG en niveaux de gris, papier clair et lignes d'écriture,
    généré ici (quelques centaines d'octets) plutôt que lu d'un fichier."""

    def morceau(genre: bytes, donnees: bytes) -> bytes:
        return struct.pack(">I", len(donnees)) + genre + donnees + struct.pack(">I", zlib.crc32(genre + donnees))

    lignes = []
    for y in range(hauteur):
        ecrite = 12 <= y < hauteur - 12 and y % 9 in (0, 1) and (y // 9) % (numero + 2) != 0
        fin = largeur - 12 - (y * 7 + numero * 13) % 40
        rangee = bytes(90 if ecrite and 10 <= x < fin else 244 for x in range(largeur))
        lignes.append(b"\x00" + rangee)
    entete = struct.pack(">IIBBBBB", largeur, hauteur, 8, 0, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + morceau(b"IHDR", entete)
        + morceau(b"IDAT", zlib.compress(b"".join(lignes), 9))
        + morceau(b"IEND", b"")
    )

def _patient_b(h: _Histoire) -> None:
    """patient-007 : un cas en cours, une ordonnance à payer qui porte un AINS, une allergie AINS."""
    p, cnhu, medecin, infirmier = "patient-007", "cnhu-hkm", "agent-02", "agent-03"
    visite = h.il_y_a(1, 15, 10)
    h.allergie("hist-b-allergie-ains", p, medecin)
    h.groupe_sanguin("hist-b-groupe-sanguin", p, medecin, "A+", visite)
    h.antecedent("hist-b-antecedent-asthme", p, medecin, "medical", "Asthme", "depuis l'enfance", True, visite)
    h.cas("hist-b-cas-douleurs", p, cnhu, medecin, "Douleurs du genou", visite)
    h.visite("hist-b-visite-1", p, "hist-b-cas-douleurs", cnhu, medecin, "consultation",
             "Douleur du genou droit après une chute", visite)
    h.quantite("hist-b-mesure-temp", p, "hist-b-visite-1", infirmier, visite, "8310-5", "Température", 37.1, "Cel", "°C")
    h.tension("hist-b-mesure-tension", p, "hist-b-visite-1", infirmier, visite, 130, 80)
    h.ligne("hist-b-ligne-ibuprofene", "ORD-3HX-9KT", p, "hist-b-visite-1", medecin, cnhu, visite,
            "MED-IBUPROFENE-400", ["matin", "soir"], 1, 5)
    h.ligne("hist-b-ligne-paracetamol", "ORD-3HX-9KT", p, "hist-b-visite-1", medecin, cnhu, visite,
            "MED-PARACETAMOL-500", ["matin", "midi", "soir"], 1, 5)
    h.acces("hist-b-acces-1", p, visite, medecin, cnhu, "soin", "relation-de-soin", "create")


def ressources(maintenant: datetime | None = None) -> list[Ressource]:
    """Toute l'histoire clinique de démonstration, datée par rapport à `maintenant` (l'instant présent)."""
    h = _Histoire(maintenant or datetime.now(timezone.utc))
    _patient_a(h)
    _patient_b(h)
    return [_avec_son_origine(r) for r in h.ressources]


# Ce que la patiente a dit d'elle-même, et ce qu'une visite a relevé (ADR 0007).
_DECLARE = {"FamilyMemberHistory", "MedicationStatement", "AllergyIntolerance"}
_EN_VISITE = {"EpisodeOfCare", "Encounter", "Observation", "Condition", "MedicationRequest"}


def _avec_son_origine(r: Ressource) -> Ressource:
    """L'origine d'une entrée de l'histoire : un antécédent, une allergie, un traitement au long cours ou
    le groupe sanguin ont été déclarés ; le reste a été relevé en visite. Les encaissements, délivrances et
    accès n'en portent pas."""
    type_ = r["resourceType"]
    categories = {c.get("code") for cat in r.get("category", []) for c in cat.get("coding", [])}
    groupe_sanguin = any(c.get("code") == "882-1" for c in r.get("code", {}).get("coding", []))
    if type_ in _DECLARE or "problem-list-item" in categories or groupe_sanguin:
        return avec_origine(r, "declaration")
    if type_ in _EN_VISITE:
        return avec_origine(r, "visite")
    return r
