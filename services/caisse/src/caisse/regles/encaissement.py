"""Ce que la caisse fait d'une ordonnance : la montrer tarifée, en encaisser des lignes.

Le caissier ne voit que les ordonnances à payer dans son établissement, et d'elles que les lignes, leurs
montants, le patient, le prescripteur et la date : rien du dossier. Aucun montant n'est saisi : chaque
prix vient du tarif de l'établissement. Une ligne ne se paie qu'une fois.
"""

import logging

from pydantic import BaseModel

from commun.fhir import caisse as fhir_caisse
from commun.fhir import dossier, systemes
from commun.fhir.client import ClientFhir, Ressource
from commun.jeton import Agent

SERVICE = "caisse"
MOTIF = "numero-d-ordonnance"

journal = logging.getLogger(SERVICE)


class OrdonnanceIntrouvable(Exception):
    """Aucune ligne sous ce numéro, ou pas à payer dans l'établissement du caissier."""


class LigneInconnue(Exception):
    """Une ligne demandée n'est pas de cette ordonnance."""


class LigneDejaPayee(Exception):
    """Une ligne demandée est déjà portée par un encaissement."""


class TarifIntrouvable(Exception):
    """Un produit de l'ordonnance n'a pas de tarif dans l'établissement."""


class NomDuPatient(BaseModel):
    nom: str
    prenoms: str


class Ligne(BaseModel):
    id: str
    libelle: str
    quantite: int
    prix_unitaire: int
    montant: int
    payee: bool


class Ordonnance(BaseModel):
    numero: str
    patient: NomDuPatient
    prescripteur: str
    date: str
    etablissement: str
    lignes: list[Ligne]
    total_a_payer: int


class LigneEncaissee(BaseModel):
    id: str
    libelle: str
    montant: int


class Recepisse(BaseModel):
    recepisse: str
    numero: str
    date: str
    etablissement: str
    montant: int
    lignes: list[LigneEncaissee]


def _qui(caissier: Agent) -> dict[str, str]:
    return dossier.reference("Practitioner", caissier.sub)


async def _tracer(fhir: ClientFhir, caissier: Agent, patient: str, action: dossier.Action, ressource: dict[str, str] | None = None) -> None:
    await dossier.tracer(
        fhir,
        patient=patient,
        qui=_qui(caissier),
        service=SERVICE,
        action=action,
        motif=MOTIF,
        etablissement=caissier.etablissement,
        ressource=ressource,
    )


async def _nom_de_l_etablissement(fhir: ClientFhir, etablissement: str) -> str:
    organisation = await fhir.lire("Organization", etablissement)
    return str(organisation.get("name", etablissement)) if organisation else etablissement


async def _lignes_servies(fhir: ClientFhir, caissier: Agent, numero: str) -> list[Ressource]:
    """Les lignes de l'ordonnance à payer dans l'établissement du caissier ; `OrdonnanceIntrouvable` sinon.

    Une ordonnance d'un autre établissement répond comme une ordonnance inconnue : la caisse ne dit
    pas qu'elle existe ailleurs.
    """
    lignes = await fhir_caisse.lignes_de_l_ordonnance(fhir, numero)
    servies = [l for l in lignes if fhir_caisse.etablissement_de_la_ligne(l) == caissier.etablissement]
    if not servies:
        raise OrdonnanceIntrouvable(numero)
    return servies


async def _tarifer(fhir: ClientFhir, etablissement: str, ligne: Ressource, payees: set[str]) -> Ligne:
    code = fhir_caisse.code_du_produit(ligne)
    prix = await fhir_caisse.prix_unitaire(fhir, etablissement, code) if code else None
    if prix is None:
        journal.error("tarif absent : ligne %s à %s", ligne["id"], etablissement)
        raise TarifIntrouvable(ligne["id"])
    quantite = fhir_caisse.quantite(ligne)
    return Ligne(
        id=ligne["id"],
        libelle=fhir_caisse.libelle_du_produit(ligne),
        quantite=quantite,
        prix_unitaire=prix,
        montant=prix * quantite,
        payee=ligne["id"] in payees,
    )


async def lire_ordonnance(fhir: ClientFhir, caissier: Agent, saisie: str) -> Ordonnance:
    """L'ordonnance `saisie` (`ord7k4m2p` comme `ORD-7K4-M2P`), tarifée, avec ses lignes déjà payées."""
    numero = dossier.normaliser_numero(saisie)
    lignes = await _lignes_servies(fhir, caissier, numero)
    premiere = lignes[0]
    patient = dossier.id_de(premiere.get("subject")) or ""
    prescripteur = dossier.id_de(premiere.get("requester"))
    # Réglée : payée à cette caisse, ou vendue en officine.
    payees = fhir_caisse.lignes_payees(await fhir_caisse.encaissements(fhir, numero))
    payees |= await fhir_caisse.lignes_vendues_en_officine(fhir, lignes)
    tarifees = [await _tarifer(fhir, caissier.etablissement, ligne, payees) for ligne in lignes]
    nom, prenoms = fhir_caisse.nom_affiche(await fhir.lire("Patient", patient))
    nom_prescripteur, prenoms_prescripteur = fhir_caisse.nom_affiche(
        await fhir.lire("Practitioner", prescripteur) if prescripteur else None
    )
    await _tracer(fhir, caissier, patient, "read")
    journal.info("ordonnance lue : %d lignes, patient %s, caissier %s", len(lignes), patient, caissier.sub)
    return Ordonnance(
        numero=numero,
        patient=NomDuPatient(nom=nom, prenoms=prenoms),
        prescripteur=f"{prenoms_prescripteur} {nom_prescripteur}".strip(),
        date=str(premiere.get("authoredOn", ""))[:10],
        etablissement=await _nom_de_l_etablissement(fhir, caissier.etablissement),
        lignes=tarifees,
        total_a_payer=sum(ligne.montant for ligne in tarifees if not ligne.payee),
    )


async def encaisser(fhir: ClientFhir, caissier: Agent, saisie: str, ids: list[str]) -> Recepisse:
    """Encaisse les lignes `ids` de l'ordonnance : un `Invoice`, et son récépissé.

    `LigneInconnue` pour une ligne hors de l'ordonnance, `LigneDejaPayee` pour une ligne déjà
    encaissée : rien n'est alors écrit.
    """
    numero = dossier.normaliser_numero(saisie)
    lignes = {ligne["id"]: ligne for ligne in await _lignes_servies(fhir, caissier, numero)}
    demandees = list(dict.fromkeys(ids))
    if not demandees or any(id_ not in lignes for id_ in demandees):
        raise LigneInconnue(numero)
    payees = fhir_caisse.lignes_payees(await fhir_caisse.encaissements(fhir, numero))
    payees |= await fhir_caisse.lignes_vendues_en_officine(fhir, list(lignes.values()))
    if payees & set(demandees):
        raise LigneDejaPayee(numero)
    tarifees = [await _tarifer(fhir, caissier.etablissement, lignes[id_], payees) for id_ in demandees]
    patient = dossier.id_de(lignes[demandees[0]].get("subject")) or ""
    recepisse = dossier.numero("REC")
    ecrit = await fhir.creer(
        fhir_caisse.invoice(
            recepisse=recepisse,
            numero=numero,
            patient=patient,
            etablissement=caissier.etablissement,
            caissier=caissier.sub,
            lignes=[(l.id, l.libelle, l.montant) for l in tarifees],
        )
    )
    await _tracer(fhir, caissier, patient, "create", dossier.reference("Invoice", ecrit["id"]))
    journal.info("encaissement %s : %d lignes, caissier %s", ecrit["id"], len(tarifees), caissier.sub)
    return _recepisse(ecrit, await _nom_de_l_etablissement(fhir, caissier.etablissement))


def _recepisse(facture: Ressource, etablissement: str) -> Recepisse:
    lignes = [LigneEncaissee(id=i, libelle=l, montant=m) for i, l, m in fhir_caisse.lignes_encaissees(facture)]
    return Recepisse(
        recepisse=fhir_caisse.identifiant(facture, systemes.RECEPISSE) or "",
        numero=fhir_caisse.identifiant(facture, systemes.ORDONNANCE) or "",
        date=str(facture.get("date", "")),
        etablissement=etablissement,
        montant=sum(ligne.montant for ligne in lignes),
        lignes=lignes,
    )


class RecepisseIntrouvable(Exception):
    """Aucun récépissé sous ce numéro dans l'établissement du caissier."""


async def lire_recepisse(fhir: ClientFhir, caissier: Agent, saisie: str) -> Recepisse:
    """Le récépissé `saisie`, pour le réimprimer : seulement s'il a été émis dans l'établissement du caissier."""
    numero = dossier.normaliser_numero(saisie, "REC")
    facture = await fhir_caisse.encaissement_par_recepisse(fhir, numero)
    if not facture or dossier.id_de(facture.get("issuer")) != caissier.etablissement:
        raise RecepisseIntrouvable(numero)
    await _tracer(fhir, caissier, dossier.id_de(facture.get("subject")) or "", "read", dossier.reference("Invoice", facture["id"]))
    return _recepisse(facture, await _nom_de_l_etablissement(fhir, caissier.etablissement))
