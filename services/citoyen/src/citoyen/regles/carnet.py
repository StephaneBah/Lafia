"""Ce que le carnet dit au citoyen, en mots simples : ses cas, son ordonnance, son traitement du jour,
qui a ouvert son dossier. Des règles pures sur le dossier lu (`commun.fhir.citoyen`), sans FHIR.

Rien de ce que le carnet rend ne porte le NPI.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel

from commun.fhir.citoyen import Acces, Cas, DossierDuCitoyen, Ligne, Mesure, Visite, instant

# L'heure du Bénin : un jour de traitement commence à minuit, à Cotonou.
FUSEAU = timezone(timedelta(hours=1))

StatutDeLigne = Literal["apayer", "paye", "aretirer", "partiel", "retire"]
Moment = Literal["matin", "midi", "soir", "nuit"]
ORDRE_DES_MOMENTS: tuple[Moment, ...] = ("matin", "midi", "soir", "nuit")

TYPES_DE_VISITE = {
    "consultation": "Consultation",
    "soins-infirmiers": "Soins infirmiers",
    "continuite": "Visite de suivi",
    "urgence": "Urgence",
}
MESSAGES_D_ORDONNANCE: dict[StatutDeLigne, str] = {
    "apayer": "Passez à la caisse avec votre reçu.",
    "paye": "C'est payé.",
    "aretirer": "C'est payé : allez à la pharmacie retirer vos médicaments.",
    "partiel": "Retournez à la pharmacie pour le médicament qui manque.",
    "retire": "Tout vous a été remis. Suivez votre traitement.",
}


# Ce que rend le service.


class Nom(BaseModel):
    prenom: str
    nom: str


class ResumeDeCas(BaseModel):
    id: str
    motif: str
    en_cours: bool
    debut: str
    fin: str | None
    etablissement: str | None
    visites: int


class MesureLue(BaseModel):
    libelle: str
    valeur: str
    alerte: bool = False
    """Hors de la normale (fièvre, tension haute, TDR positif) : dit par un mot, pas par la couleur."""


class VisiteLue(BaseModel):
    id: str
    date: str
    type: str
    urgence: bool
    etablissement: str | None
    soignant: str | None
    motif: str | None
    mesures: list[MesureLue]
    diagnostics: list[str]
    ordonnance: str | None


class DetailDeCas(ResumeDeCas):
    visites_lues: list[VisiteLue]


class LigneLue(BaseModel):
    id: str
    produit: str
    statut: StatutDeLigne
    moments: list[Moment]
    par_prise: float | None
    jours: int | None
    quantite: float | None
    remis: float
    unite: str | None


class OrdonnanceLue(BaseModel):
    numero: str
    date: str
    etablissement: str | None
    statut: StatutDeLigne
    message: str
    lignes: list[LigneLue]


class Prise(BaseModel):
    produit: str
    par_prise: float | None
    unite: str | None
    jour: int
    """Le jour du traitement, à partir de 1."""
    jours: int


class TraitementDuJour(BaseModel):
    date: str
    moments: dict[Moment, list[Prise]]
    prochain: Moment | None
    """Le prochain moment d'aujourd'hui où quelque chose est à prendre."""


class AccesLu(BaseModel):
    date: str
    vous: bool
    qui: str
    role: str | None
    etablissement: str | None
    service: str | None
    motif: str
    urgence: bool
    raison: str | None


class Accueil(BaseModel):
    prenom: str
    nom: str
    cas_en_cours: int
    cas_recent: ResumeDeCas | None
    ordonnance: OrdonnanceLue | None
    prochain_moment: Moment | None
    prises_au_prochain_moment: int
    dernier_acces: AccesLu | None
    allergies: list[str]


# Les règles.


def jour_local(texte: str) -> date | None:
    moment = instant(texte)
    if moment is None:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=FUSEAU)
    return moment.astimezone(FUSEAU).date()


def aujourd_hui() -> date:
    return datetime.now(FUSEAU).date()


def statut_de_ligne(ligne: Ligne, dossier: DossierDuCitoyen) -> StatutDeLigne:
    """À payer tant qu'aucun encaissement ne la porte ; un acte ou un examen payé est payé, jamais remis ;
    un médicament payé est à retirer, retiré en partie, ou retiré selon la somme de ses délivrances."""
    if ligne.id not in dossier.payees:
        return "apayer"
    if ligne.code and not ligne.code.startswith("MED-"):
        return "paye"
    remis = dossier.remis.get(ligne.id, 0)
    if remis <= 0:
        return "aretirer"
    if ligne.quantite is not None and remis < ligne.quantite:
        return "partiel"
    return "retire"


def statut_d_ordonnance(statuts: list[StatutDeLigne]) -> StatutDeLigne:
    """L'état d'une ordonnance, de celui de ses lignes : ce qu'il reste à faire d'abord."""
    ensemble = set(statuts)
    if not ensemble or "apayer" in ensemble:
        return "apayer"
    if ensemble <= {"retire", "paye"}:
        return "retire"
    if "partiel" in ensemble or "retire" in ensemble:
        return "partiel"
    return "aretirer"


def _nombre(valeur: float) -> str:
    texte = f"{valeur:g}"
    return texte.replace(".", ",")


def mesure_lue(mesure: Mesure) -> MesureLue:
    """Une mesure en mots : la valeur et, quand elle sort de la normale, le mot qui le dit."""
    if mesure.systolique is not None and mesure.diastolique is not None:
        # En mm[Hg] au noyau ; dite comme au Bénin, en centimètres : 120/80 se dit « 12/8 ».
        haute = mesure.systolique >= 140 or mesure.diastolique >= 90
        valeur = f"{_nombre(mesure.systolique / 10)}/{_nombre(mesure.diastolique / 10)}"
        return MesureLue(libelle="Tension", valeur=valeur + (" : haute" if haute else ""), alerte=haute)
    if mesure.resultat is not None:
        positif = mesure.resultat.lower().startswith("positi")
        return MesureLue(libelle=mesure.libelle, valeur=mesure.resultat, alerte=positif)
    if mesure.valeur is None:
        return MesureLue(libelle=mesure.libelle, valeur="—")
    valeur = f"{_nombre(mesure.valeur)} {mesure.unite or ''}".strip()
    if mesure.loinc == "8310-5":
        fievre = mesure.valeur >= 38
        return MesureLue(libelle="Température", valeur=valeur + (" : fièvre" if fievre else ""), alerte=fievre)
    return MesureLue(libelle=mesure.libelle, valeur=valeur)


def _resume(cas: Cas, dossier: DossierDuCitoyen) -> ResumeDeCas:
    return ResumeDeCas(
        id=cas.id,
        motif=cas.motif,
        en_cours=cas.en_cours,
        debut=cas.debut,
        fin=cas.fin,
        etablissement=dossier.noms.get(cas.etablissement or ""),
        visites=sum(1 for v in dossier.visites if v.cas == cas.id),
    )


def liste_des_cas(dossier: DossierDuCitoyen) -> list[ResumeDeCas]:
    """Les cas, en cours d'abord, puis du plus récent au plus ancien."""
    tries = sorted(dossier.cas, key=lambda c: c.debut, reverse=True)
    return [_resume(c, dossier) for c in sorted(tries, key=lambda c: not c.en_cours)]


def _visite_lue(visite: Visite, dossier: DossierDuCitoyen) -> VisiteLue:
    diagnostics = [
        d.libelle + ("" if d.confirme else " (à confirmer)") + (f". {d.note}" if d.note else "")
        for d in dossier.diagnostics
        if d.visite == visite.id
    ]
    numero = next((ligne.numero for ligne in dossier.lignes if ligne.visite == visite.id and ligne.numero), None)
    return VisiteLue(
        id=visite.id,
        date=visite.date,
        type=TYPES_DE_VISITE.get(visite.type, "Visite"),
        urgence=visite.urgence,
        etablissement=dossier.noms.get(visite.etablissement or ""),
        soignant=dossier.noms.get(visite.soignant or ""),
        motif=visite.motif,
        mesures=[mesure_lue(m) for m in dossier.mesures if m.visite == visite.id],
        diagnostics=diagnostics,
        ordonnance=numero,
    )


def detail_du_cas(dossier: DossierDuCitoyen, id_: str) -> DetailDeCas | None:
    """Un cas du citoyen et ses visites dans l'ordre ; None quand ce n'est pas un de ses cas."""
    cas = next((c for c in dossier.cas if c.id == id_), None)
    if cas is None:
        return None
    visites = sorted((v for v in dossier.visites if v.cas == id_), key=lambda v: v.date)
    return DetailDeCas(**_resume(cas, dossier).model_dump(), visites_lues=[_visite_lue(v, dossier) for v in visites])


def ordonnances(dossier: DossierDuCitoyen) -> list[OrdonnanceLue]:
    """Les ordonnances, de la plus récente à la plus ancienne, chaque ligne avec son état."""
    par_numero: dict[str, list[Ligne]] = {}
    for ligne in dossier.lignes:
        par_numero.setdefault(ligne.numero or ligne.id, []).append(ligne)
    lues = []
    for numero, lignes in par_numero.items():
        lignes_lues = [
            LigneLue(
                id=ligne.id,
                produit=ligne.produit,
                statut=statut_de_ligne(ligne, dossier),
                moments=[m for m in ORDRE_DES_MOMENTS if m in ligne.moments],
                par_prise=ligne.par_prise,
                jours=ligne.jours,
                quantite=ligne.quantite,
                remis=dossier.remis.get(ligne.id, 0),
                unite=ligne.unite,
            )
            for ligne in sorted(lignes, key=lambda ligne: ligne.produit)
        ]
        statut = statut_d_ordonnance([ligne.statut for ligne in lignes_lues])
        lues.append(
            OrdonnanceLue(
                numero=numero,
                date=min(ligne.date for ligne in lignes),
                etablissement=dossier.noms.get(lignes[0].etablissement or ""),
                statut=statut,
                message=MESSAGES_D_ORDONNANCE[statut],
                lignes=lignes_lues,
            )
        )
    return sorted(lues, key=lambda o: o.date, reverse=True)


def traitement_du_jour(dossier: DossierDuCitoyen, jour: date, heure: int = 0) -> TraitementDuJour:
    """Ce qu'il y a à prendre ce jour, par moment. Une ligne court du jour de sa prescription pendant
    son nombre de jours : prescrite il y a trois jours pour cinq jours, elle en est à son quatrième."""
    moments: dict[Moment, list[Prise]] = {m: [] for m in ORDRE_DES_MOMENTS}
    for ligne in dossier.lignes:
        debut = jour_local(ligne.date)
        if debut is None or not ligne.jours or (ligne.code and not ligne.code.startswith("MED-")):
            continue
        rang = (jour - debut).days
        if not 0 <= rang < ligne.jours:
            continue
        for moment in ligne.moments:
            moments[moment].append(  # type: ignore[index]
                Prise(produit=ligne.produit, par_prise=ligne.par_prise, unite=ligne.unite, jour=rang + 1, jours=ligne.jours)
            )
    # Le prochain moment : matin avant 11 h, midi avant 15 h, soir avant 20 h, nuit ensuite.
    fins = {"matin": 11, "midi": 15, "soir": 20, "nuit": 24}
    prochain = next((m for m in ORDRE_DES_MOMENTS if moments[m] and heure < fins[m]), None)
    return TraitementDuJour(date=jour.isoformat(), moments=moments, prochain=prochain)


def journal_des_acces(dossier: DossierDuCitoyen) -> list[AccesLu]:
    """Qui a ouvert le dossier, du plus récent au plus ancien. Les ouvertures du citoyen lui-même, qui
    se suivent, n'en font qu'une : la plus récente."""
    moi = f"Patient/{dossier.patient['id']}"
    lus: list[AccesLu] = []
    for acces in sorted(dossier.acces, key=lambda a: a.date, reverse=True):
        vous = acces.qui == moi
        if vous and lus and lus[-1].vous:
            continue
        lus.append(_acces_lu(acces, vous, dossier))
    return lus


def _acces_lu(acces: Acces, vous: bool, dossier: DossierDuCitoyen) -> AccesLu:
    urgence = acces.motif == "acces-urgence"
    if vous:
        qui, motif = "Vous", "Vous avez ouvert votre carnet"
    else:
        qui = dossier.noms.get(acces.qui or "", "Un agent de santé")
        if dossier.roles.get(acces.qui or "") == "médecin":
            qui = f"Dr {qui}"
        motif = {
            "relation-de-soin": "Pour vous soigner",
            "acces-urgence": "Accès d'urgence",
            "numero-d-ordonnance": {
                "caisse": "Votre ordonnance seulement, pour l'encaisser",
                "pharmacie": "Votre ordonnance et vos allergies, pour vous remettre les médicaments",
            }.get(acces.service or "", "Votre ordonnance seulement"),
        }.get(acces.motif or "", "Consultation du dossier")
    return AccesLu(
        date=acces.date,
        vous=vous,
        qui=qui,
        role=None if vous else dossier.roles.get(acces.qui or ""),
        etablissement=dossier.noms.get(acces.etablissement or ""),
        service=acces.service,
        motif=motif,
        urgence=urgence,
        raison=acces.raison if urgence else None,
    )


def accueil(dossier: DossierDuCitoyen, maintenant: datetime) -> Accueil:
    """L'accueil du carnet : où en est le citoyen, en une phrase et quatre portes."""
    cas = liste_des_cas(dossier)
    en_cours = [c for c in cas if c.en_cours]
    lues = ordonnances(dossier)
    # L'ordonnance à suivre : la plus récente où il reste à faire, sinon la plus récente.
    ordonnance = next((o for o in lues if o.statut != "retire"), lues[0] if lues else None)
    local = maintenant.astimezone(FUSEAU)
    traitement = traitement_du_jour(dossier, local.date(), local.hour)
    autres = [a for a in journal_des_acces(dossier) if not a.vous]
    return Accueil(
        prenom=dossier.prenom,
        nom=dossier.nom,
        cas_en_cours=len(en_cours),
        cas_recent=(en_cours or cas or [None])[0],
        ordonnance=ordonnance,
        prochain_moment=traitement.prochain,
        prises_au_prochain_moment=len(traitement.moments[traitement.prochain]) if traitement.prochain else 0,
        dernier_acces=autres[0] if autres else None,
        allergies=dossier.allergies,
    )
