"""Une ordonnance vue d'une officine, et la vente qu'elle en déclare.

L'officine atteint l'ordonnance par son numéro, sans relation de soin : elle voit qui l'a prescrite,
quand, dans quel établissement, et ce qui reste à remettre de chaque médicament ; jamais le patient.
Lit le noyau par `commun.fhir.pharmacie`, décide par `pharmacie.regles.vente`, trace chaque accès.
Le journal ne cite que des identifiants : ni nom, ni NPI, ni contenu clinique.
"""

import asyncio
import logging
from dataclasses import dataclass

from pydantic import BaseModel

from commun.fhir import dossier
from commun.fhir import pharmacie as fhir_pharmacie
from commun.fhir.client import ClientFhir
from commun.jeton import Officine
from pharmacie.ordonnance import MOTIF, SERVICE, Delivrance, Delivrances, Introuvable, PosologieVue
from pharmacie.regles import delivrance as regles_delivrance
from pharmacie.regles import vente as regles

journal = logging.getLogger(SERVICE)


class LigneVendable(BaseModel):
    id: str
    libelle: str
    prescrite: int
    remise: int
    reste: int
    posologie: PosologieVue
    vendable: bool
    raison: str | None = None


class OrdonnanceEnOfficine(BaseModel):
    numero: str
    prescripteur: str | None
    date: str | None
    etablissement: str | None
    lignes: list[LigneVendable]


@dataclass(frozen=True)
class _Lu:
    numero: str
    lignes: list[fhir_pharmacie.Ligne]
    etats: dict[str, regles_delivrance.EtatDeLigne]
    patient: str


async def _lire(fhir: ClientFhir, saisie: str) -> _Lu:
    numero = dossier.normaliser_numero(saisie)
    lignes = [l for l in await fhir_pharmacie.lignes_de_l_ordonnance(fhir, numero) if regles.se_vend(l.code)]
    if not lignes or not lignes[0].patient:
        raise Introuvable(numero)
    payees, remises = await asyncio.gather(
        fhir_pharmacie.lignes_payees(fhir, numero),
        asyncio.gather(*(fhir_pharmacie.quantite_remise(fhir, l.id) for l in lignes)),
    )
    etats = {
        l.id: regles_delivrance.EtatDeLigne(payee=l.id in payees, prescrite=l.prescrite, remise=remise)
        for l, remise in zip(lignes, remises)
    }
    return _Lu(numero, lignes, etats, lignes[0].patient)


async def _tracer(fhir: ClientFhir, lu: _Lu, officine: Officine, action: dossier.Action, ressource: str | None = None) -> None:
    await dossier.tracer(
        fhir,
        patient=lu.patient,
        qui=dossier.reference("Organization", officine.sub),
        service=SERVICE,
        action=action,
        motif=MOTIF,
        ressource=dossier.reference("MedicationDispense", ressource) if ressource else None,
    )


async def consulter(fhir: ClientFhir, saisie: str, officine: Officine) -> OrdonnanceEnOfficine:
    """L'ordonnance vue de l'officine : de quoi la vérifier, et ce qu'elle peut en vendre."""
    lu = await _lire(fhir, saisie)
    premiere = lu.lignes[0]
    prescripteur, etablissement = await asyncio.gather(
        fhir_pharmacie.nom_du_prescripteur(fhir, premiere.prescripteur),
        fhir_pharmacie.nom_de_l_organisation(fhir, premiere.etablissement),
    )
    await _tracer(fhir, lu, officine, "read")
    journal.info("ordonnance consultée en officine %s : patient %s, %d lignes", officine.sub, lu.patient, len(lu.lignes))
    lignes = []
    for l in lu.lignes:
        etat = lu.etats[l.id]
        verdict = regles.vendabilite(etat, etablissement)
        lignes.append(
            LigneVendable(
                id=l.id,
                libelle=l.libelle,
                prescrite=etat.prescrite,
                remise=etat.remise,
                reste=regles_delivrance.reste(etat.prescrite, etat.remise),
                posologie=PosologieVue(**l.posologie.__dict__),
                vendable=verdict.vendable,
                raison=verdict.raison,
            )
        )
    return OrdonnanceEnOfficine(
        numero=lu.numero, prescripteur=prescripteur, date=premiere.date, etablissement=etablissement, lignes=lignes
    )


async def vendre(fhir: ClientFhir, saisie: str, officine: Officine, demande: list[tuple[str, int]]) -> Delivrances:
    """Écrit la vente déclarée, une `MedicationDispense` par ligne ; `DelivranceRefusee` quand elle
    ne peut pas s'écrire."""
    lu = await _lire(fhir, saisie)
    regles.verifier(demande, lu.etats)
    par_id = {l.id: l for l in lu.lignes}
    faites = []
    for id_, quantite in demande:
        ligne = par_id[id_]
        ecrite = await fhir.creer(fhir_pharmacie.vente_d_officine(ligne, quantite, officine.sub))
        await _tracer(fhir, lu, officine, "create", ecrite["id"])
        etat = lu.etats[id_]
        faites.append(
            Delivrance(
                id=ecrite["id"],
                ligne=id_,
                libelle=ligne.libelle,
                quantite=quantite,
                reste=regles_delivrance.reste(etat.prescrite, etat.remise + quantite),
            )
        )
    journal.info("vente en officine %s : patient %s, lignes %s", officine.sub, lu.patient, ",".join(i for i, _ in demande))
    return Delivrances(delivrances=faites)
