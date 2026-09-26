"""Une ordonnance vue du comptoir de la pharmacie, et sa délivrance.

Lit le noyau par `commun.fhir.pharmacie`, décide par `pharmacie.regles.delivrance`, trace chaque
accès au dossier. Le journal ne cite que des identifiants : ni nom, ni NPI, ni contenu clinique.
"""

import asyncio
import logging
from dataclasses import dataclass

from pydantic import BaseModel

from commun.fhir import dossier
from commun.fhir import pharmacie as fhir_pharmacie
from commun.fhir.client import ClientFhir
from commun.jeton import Agent
from pharmacie.regles import delivrance as regles

SERVICE = "pharmacie"
MOTIF = "numero-d-ordonnance"

journal = logging.getLogger(SERVICE)


class PosologieVue(BaseModel):
    moments: list[str]
    jours: int | None
    dose: float | None
    texte: str | None


class LigneVue(BaseModel):
    id: str
    libelle: str
    prescrite: int
    payee: bool
    remise: int
    reste: int
    statut: regles.Statut
    posologie: PosologieVue


class PatientVu(BaseModel):
    nom: str
    prenoms: str


class AllergieVue(BaseModel):
    libelle: str
    lignes: list[str]


class OrdonnanceVue(BaseModel):
    numero: str
    patient: PatientVu
    prescripteur: str | None
    date: str | None
    lignes: list[LigneVue]
    allergies: list[AllergieVue]


class Delivrance(BaseModel):
    id: str
    ligne: str
    libelle: str
    quantite: int
    reste: int


class Delivrances(BaseModel):
    delivrances: list[Delivrance]


class Introuvable(Exception):
    """Aucune ligne remettable ne porte ce numéro."""


class AutreEtablissement(Exception):
    """L'ordonnance se sert dans un autre établissement que celui du pharmacien."""


@dataclass(frozen=True)
class _Lu:
    numero: str
    lignes: list[fhir_pharmacie.Ligne]
    etats: dict[str, regles.EtatDeLigne]
    patient: str
    allergies: list[regles.AllergieConcernee]


async def _lire(fhir: ClientFhir, saisie: str, pharmacien: Agent) -> _Lu:
    numero = dossier.normaliser_numero(saisie)
    lignes = [l for l in await fhir_pharmacie.lignes_de_l_ordonnance(fhir, numero) if regles.se_remet(l.code)]
    if not lignes or not lignes[0].patient:
        raise Introuvable(numero)
    if any(l.etablissement != pharmacien.etablissement for l in lignes):
        raise AutreEtablissement(numero)
    patient = lignes[0].patient
    payees, remises, allergies = await asyncio.gather(
        fhir_pharmacie.lignes_payees(fhir, numero),
        asyncio.gather(*(fhir_pharmacie.quantite_remise(fhir, l.id) for l in lignes)),
        fhir_pharmacie.allergies_du_patient(fhir, patient),
    )
    etats = {
        l.id: regles.EtatDeLigne(payee=l.id in payees, prescrite=l.prescrite, remise=remise)
        for l, remise in zip(lignes, remises)
    }
    concernees = regles.allergies_concernees(((a.libelle, a.atc) for a in allergies), {l.id: l.atc for l in lignes})
    return _Lu(numero, lignes, etats, patient, concernees)


async def consulter(fhir: ClientFhir, saisie: str, pharmacien: Agent) -> OrdonnanceVue:
    """L'ordonnance au comptoir : ses lignes remettables, leur état, les allergies qui les concernent."""
    lu = await _lire(fhir, saisie, pharmacien)
    premiere = lu.lignes[0]
    (nom, prenoms), prescripteur = await asyncio.gather(
        fhir_pharmacie.nom_du_patient(fhir, lu.patient),
        fhir_pharmacie.nom_du_prescripteur(fhir, premiere.prescripteur),
    )
    await dossier.tracer(
        fhir,
        patient=lu.patient,
        qui=dossier.reference("Practitioner", pharmacien.sub),
        service=SERVICE,
        action="read",
        motif=MOTIF,
        etablissement=pharmacien.etablissement,
    )
    journal.info("ordonnance consultée : patient %s, %d lignes", lu.patient, len(lu.lignes))
    lignes = []
    for l in lu.lignes:
        etat = lu.etats[l.id]
        lignes.append(
            LigneVue(
                id=l.id,
                libelle=l.libelle,
                prescrite=etat.prescrite,
                payee=etat.payee,
                remise=etat.remise,
                reste=regles.reste(etat.prescrite, etat.remise),
                statut=regles.statut(etat.payee, etat.prescrite, etat.remise),
                posologie=PosologieVue(**l.posologie.__dict__),
            )
        )
    return OrdonnanceVue(
        numero=lu.numero,
        patient=PatientVu(nom=nom, prenoms=prenoms),
        prescripteur=prescripteur,
        date=premiere.date,
        lignes=lignes,
        allergies=[AllergieVue(libelle=a.libelle, lignes=a.lignes) for a in lu.allergies],
    )


async def delivrer(
    fhir: ClientFhir, saisie: str, pharmacien: Agent, demande: list[tuple[str, int]], allergie_reconnue: bool
) -> Delivrances:
    """Écrit la remise des lignes demandées, une `MedicationDispense` par ligne ; `DelivranceRefusee`
    quand elle ne peut pas s'écrire."""
    lu = await _lire(fhir, saisie, pharmacien)
    allergiques = {id_ for a in lu.allergies for id_ in a.lignes}
    regles.verifier(demande, lu.etats, allergiques, allergie_reconnue)
    par_id = {l.id: l for l in lu.lignes}
    faites = []
    for id_, quantite in demande:
        ligne = par_id[id_]
        ecrite = await fhir.creer(
            fhir_pharmacie.medication_dispense(ligne, quantite, pharmacien.sub, pharmacien.etablissement)
        )
        await dossier.tracer(
            fhir,
            patient=lu.patient,
            qui=dossier.reference("Practitioner", pharmacien.sub),
            service=SERVICE,
            action="create",
            motif=MOTIF,
            etablissement=pharmacien.etablissement,
            ressource=dossier.reference("MedicationDispense", ecrite["id"]),
        )
        etat = lu.etats[id_]
        faites.append(
            Delivrance(
                id=ecrite["id"],
                ligne=id_,
                libelle=ligne.libelle,
                quantite=quantite,
                reste=regles.reste(etat.prescrite, etat.remise + quantite),
            )
        )
    journal.info(
        "délivrance : patient %s, lignes %s%s",
        lu.patient,
        ",".join(id_ for id_, _ in demande),
        ", allergie reconnue" if allergie_reconnue and allergiques else "",
    )
    return Delivrances(delivrances=faites)
