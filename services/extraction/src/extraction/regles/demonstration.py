"""L'Extraction de démonstration (ADR 0009) : elle répond au contrat comme le modèle le fera, sans rien lire.

Aucun modèle de lecture n'existe encore. En attendant, chaque type de Document reçoit un brouillon de
Transcription (ADR 0010) et des propositions, fixes, qui ressemblent à ce qu'un vrai Document de ce type
porterait : de quoi faire tourner la Relecture, le Contrôle, la validation et l'écriture au dossier de
bout en bout. Le modèle rendu, `demonstration:0`, fait dire à chaque écran « extraction de
démonstration ». Rien ici ne dépend du contenu des pages, seulement de leur nombre : le brouillon ne
renvoie qu'à des pages qui existent, et un long Document y gagne un volet illisible.

Chaque proposition est une ressource FHIR R4 des sortes que le dossier tient déjà, sans id, sans sujet
et sans auteur : le service `relecture` les remplit à la validation. Chaque Coding porte son libellé,
chaque CodeableConcept son texte.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from commun.extraction import MODELE_DE_DEMONSTRATION, Extraction, Proposition
from commun.fhir import systemes

STATUT_CLINIQUE = "http://terminology.hl7.org/CodeSystem/condition-clinical"
STATUT_CLINIQUE_D_ALLERGIE = "http://terminology.hl7.org/CodeSystem/allergyintolerance-clinical"
VERIFICATION_D_ALLERGIE = "http://terminology.hl7.org/CodeSystem/allergyintolerance-verification"
CATEGORIE_D_OBSERVATION = "http://terminology.hl7.org/CodeSystem/observation-category"

AVERTISSEMENT = (
    "Extraction de démonstration : aucun modèle n'a lu ce document. Le texte et les propositions "
    "ci-dessous sont des exemples fixes, les mêmes pour chaque document de ce type."
)


def _concept(systeme: str, code: str, libelle: str) -> dict[str, Any]:
    return {"coding": [{"system": systeme, "code": code, "display": libelle}], "text": libelle}


def _antecedent(code: str, libelle: str, cim_10: str, depuis: str, *, actif: bool) -> dict[str, Any]:
    return {
        "resourceType": "Condition",
        "category": [
            _concept(systemes.CATEGORIE_DE_CONDITION, "problem-list-item", "Antécédent"),
            _concept(systemes.TYPE_D_ANTECEDENT, "medical", "Médical"),
        ],
        "clinicalStatus": _concept(STATUT_CLINIQUE, "active" if actif else "resolved", "Actif" if actif else "Résolu"),
        "verificationStatus": _concept(systemes.VERIFICATION, "unconfirmed", "Non confirmé"),
        "code": {
            "coding": [
                {"system": systemes.DIAGNOSTIC, "code": code, "display": libelle},
                {"system": systemes.CIM_10, "code": cim_10, "display": libelle},
            ],
            "text": libelle,
        },
        "onsetString": depuis,
    }


def _allergie_a_la_penicilline() -> dict[str, Any]:
    return {
        "resourceType": "AllergyIntolerance",
        "clinicalStatus": _concept(STATUT_CLINIQUE_D_ALLERGIE, "active", "Active"),
        "verificationStatus": _concept(VERIFICATION_D_ALLERGIE, "unconfirmed", "Non confirmée"),
        "category": ["medication"],
        "code": {"coding": [{"system": systemes.ATC, "code": "J01C", "display": "Pénicillines"}], "text": "Pénicilline"},
    }


def _mesure(categorie: str, libelle_de_categorie: str, loinc: str, libelle: str, valeur: float, unite: str) -> dict[str, Any]:
    """Une mesure lue sur le papier. Sa date est celle du papier : `relecture` la tient du Document."""
    return {
        "resourceType": "Observation",
        "status": "final",
        "category": [_concept(CATEGORIE_D_OBSERVATION, categorie, libelle_de_categorie)],
        "code": _concept(systemes.LOINC, loinc, libelle),
        "valueQuantity": {"value": valeur, "unit": unite, "system": systemes.UCUM, "code": unite},
    }


def _traitement_antipaludeen() -> dict[str, Any]:
    return {
        "resourceType": "MedicationStatement",
        "status": "completed",
        "medicationCodeableConcept": {
            "coding": [{"system": systemes.ATC, "code": "P01BF01", "display": "Artéméther et luméfantrine"}],
            "text": "Artéméther-luméfantrine 20/120 mg",
        },
        "dosage": [{"text": "4 comprimés matin et soir, 3 jours"}],
    }


# Par type de Document (`commun.fhir.documents.TYPES_DE_DOCUMENT`) : les lignes du texte « lu », et les
# propositions, chacune avec la confiance du modèle et le passage du texte où il l'a lue.
EXEMPLES: dict[str, tuple[list[str], list[Proposition]]] = {
    "carnet": (
        ["Antécédents : paludisme en 2019.", "Allergie : pénicilline.", "Consultation : T° 38,5 °C."],
        [
            Proposition(
                ressource=_antecedent("paludisme", "Paludisme", "B54", "2019", actif=False),
                confiance=0.82,
                extrait="Antécédents : paludisme en 2019.",
            ),
            Proposition(ressource=_allergie_a_la_penicilline(), confiance=0.74, extrait="Allergie : pénicilline."),
            Proposition(
                ressource=_mesure("vital-signs", "Signes vitaux", "8310-5", "Température corporelle", 38.5, "Cel"),
                confiance=0.68,
                extrait="Consultation : T° 38,5 °C.",
            ),
        ],
    ),
    "resultat-analyse": (
        ["Numération formule sanguine.", "Hémoglobine : 10,2 g/dL."],
        [
            Proposition(
                ressource=_mesure("laboratory", "Laboratoire", "718-7", "Hémoglobine", 10.2, "g/dL"),
                confiance=0.86,
                extrait="Hémoglobine : 10,2 g/dL.",
            ),
        ],
    ),
    "ordonnance": (
        ["Artéméther-luméfantrine 20/120 mg : 4 comprimés matin et soir, 3 jours."],
        [
            Proposition(
                ressource=_traitement_antipaludeen(),
                confiance=0.77,
                extrait="Artéméther-luméfantrine 20/120 mg : 4 comprimés matin et soir, 3 jours.",
            ),
        ],
    ),
    "compte-rendu": (
        ["Compte rendu de consultation.", "Hypertension artérielle connue, suivie depuis 2016."],
        [
            Proposition(
                ressource=_antecedent("hta", "Hypertension artérielle", "I10", "2016", actif=True),
                confiance=0.63,
                extrait="Hypertension artérielle connue, suivie depuis 2016.",
            ),
        ],
    ),
}


# Le brouillon de Transcription (ADR 0010). Chaque type de Document a ses volets, en ordre de date ; les
# pages du Document leur sont réparties dans l'ordre du papier, de sorte que chaque `p.` et chaque image
# renvoient à une page qui existe. Les établissements sont ceux qu'un carnet béninois porterait.


@dataclass(frozen=True)
class _Volet:
    type: str
    date: str | None
    etablissement: str | None
    corps: Callable[[int, int], list[str]]
    """Les lignes du volet, selon la première et la dernière de ses pages."""


def _photo(legende: str, page: int) -> str:
    return f"![{legende}](page:{page})"


def _region(legende: str, page: int, x: int, y: int, largeur: int, hauteur: int) -> str:
    """Une région de la page, en millièmes : son coin en haut à gauche, sa largeur, sa hauteur."""
    return f"![{legende}](page:{page}#{x},{y},{largeur},{hauteur})"


CS_KPANROUN = "CS Kpanroun"
CHD_OUEME = "CHD Ouémé"
HZ_CALAVI = "HZ Abomey-Calavi"
CS_GODOMEY = "CS Godomey"
CNHU = "CNHU-HKM"
CHU_MEL = "CHU-MEL"
HZ_SURU_LERE = "HZ Suru-Léré"

VOLETS: dict[str, list[_Volet]] = {
    "carnet": [
        _Volet(
            "vaccination",
            "2014-11-05",
            CS_KPANROUN,
            lambda d, f: [
                "Vaccin antitétanique (VAT 2).",
                "Prochain rendez-vous noté : mai 2015.",
                "",
                _region("Cachet du centre de santé", f, 550, 700, 400, 250),
            ],
        ),
        _Volet(
            "consultation",
            "2019-03-14",
            CS_KPANROUN,
            lambda d, f: [
                "Motif : fièvre depuis trois jours, frissons.",
                "Consultation : T° 38,5 °C.",
                "Antécédents : paludisme en 2019.",
                "Allergie : pénicilline.",
                "Conclusion : paludisme simple ; traitement par artéméther-luméfantrine.",
            ],
        ),
        _Volet(
            "analyse",
            "2019-03-15",
            CHD_OUEME,
            lambda d, f: [
                "| Examen | Résultat | Unité |",
                "|---|---|---|",
                "| Goutte épaisse | Positive | |",
                "| Hémoglobine | 10,2 | g/dL |",
                "",
                _photo("Feuille de résultats", d),
            ],
        ),
        _Volet(
            "ordonnance",
            "2019-03-15",
            CS_KPANROUN,
            lambda d, f: [
                "- Artéméther-luméfantrine 20/120 mg : 4 comprimés matin et soir, 3 jours",
                "- Paracétamol 500 mg : 1 comprimé si fièvre",
            ],
        ),
        _Volet(
            "consultation",
            "2021-08-20",
            HZ_CALAVI,
            lambda d, f: ["Motif : céphalées.", "TA 150/95 mmHg.", "Conseils hygiéno-diététiques ; contrôle dans un mois."],
        ),
    ],
    "resultat-analyse": [
        _Volet(
            "analyse",
            "2018-07-09",
            CNHU,
            lambda d, f: [
                "Numération formule sanguine.",
                "",
                "| Examen | Résultat | Unité |",
                "|---|---|---|",
                "| Hémoglobine | 10,2 | g/dL |",
                "| Globules blancs | 7,8 | 10³/µL |",
                "| Plaquettes | 245 | 10³/µL |",
                "",
                _photo("Feuille de résultats", d),
            ],
        ),
        _Volet(
            "analyse",
            "2018-07-10",
            CNHU,
            lambda d, f: ["Goutte épaisse : négative.", "", _region("Signature du biologiste", f, 600, 820, 350, 150)],
        ),
    ],
    "ordonnance": [
        _Volet(
            "ordonnance",
            "2020-02-11",
            CS_GODOMEY,
            lambda d, f: [
                "- Artéméther-luméfantrine 20/120 mg : 4 comprimés matin et soir, 3 jours",
                "- Fer et acide folique : 1 comprimé par jour, 1 mois",
                "",
                _photo("L'ordonnance", d),
                "",
                _region("Signature et cachet du prescripteur", f, 500, 750, 450, 200),
            ],
        ),
    ],
    "compte-rendu": [
        _Volet(
            "hospitalisation",
            "2016-04-02",
            CHD_OUEME,
            lambda d, f: [
                "Compte rendu de consultation.",
                "Hypertension artérielle connue, suivie depuis 2016.",
                "Hospitalisée du 2 au 6 avril pour une crise hypertensive ; sortie sous amlodipine 5 mg.",
                "",
                _photo("Première page du compte rendu", d),
            ],
        ),
        _Volet(
            "consultation",
            "2016-05-10",
            CHD_OUEME,
            lambda d, f: ["Consultation de suivi : TA 135/85 mmHg.", "", _region("Tampon du service", f, 50, 800, 300, 150)],
        ),
    ],
    "imagerie": [
        _Volet(
            "imagerie",
            "2017-10-23",
            CHU_MEL,
            lambda d, f: [
                "Échographie abdominale : foie de taille normale, pas d'épanchement.",
                "Conclusion : examen normal.",
                "",
                _photo("Le compte rendu d'échographie", d),
                "",
                _region("Cliché joint", f, 100, 300, 800, 400),
            ],
        ),
    ],
    "certificat": [
        _Volet(
            "certificat",
            "2022-01-17",
            HZ_SURU_LERE,
            lambda d, f: [
                "Certificat médical d'aptitude à la pratique du sport.",
                "Examen clinique normal.",
                "",
                _photo("Le certificat", d),
                "",
                _region("Signature et cachet du médecin", f, 500, 780, 450, 180),
            ],
        ),
    ],
    "autre": [
        _Volet(
            "autre",
            None,
            None,
            lambda d, f: [
                "Feuille manuscrite sans en-tête : contenu à préciser d'après les pages.",
                "",
                _photo("La feuille", d),
                "",
                _region("Mention en marge", f, 0, 400, 200, 300),
            ],
        ),
    ],
}

NOTE = (
    "Lecture de démonstration : aucun modèle n'a lu ces pages. Ce brouillon est un exemple, le même pour "
    "chaque document de ce type ; corrigez-le d'après les pages, volet par volet."
)
ILLISIBLE = "Écriture illisible sur cette page ; à transcrire si la relecture la déchiffre, sinon à laisser ainsi."
PAGES_POUR_UN_VOLET_ILLISIBLE = 4
"""Un Document d'au moins quatre pages reçoit un volet illisible, avant son dernier volet."""


def _tranches(pages: int, parts: int) -> list[tuple[int, int]]:
    """`parts` tranches de pages, dans l'ordre, qui couvrent 1..`pages` ; quand les pages manquent, des
    tranches voisines partagent une page. Jamais une page hors du Document."""
    tranches = []
    for rang in range(parts):
        debut = min(pages, rang * pages // parts + 1)
        fin = max(debut, (rang + 1) * pages // parts)
        tranches.append((debut, fin))
    return tranches


def _titre(type_: str, date: str | None, etablissement: str | None, debut: int, fin: int) -> str:
    renvoi = f"p. {debut}" if debut == fin else f"p. {debut}-{fin}"
    return f"## {type_} · {date or '?'} · {etablissement or '?'} · {renvoi}"


def transcription(type_de_document: str, pages: int) -> str:
    """Le brouillon de Transcription d'un Document de ce type et de `pages` pages : l'en-tête, un volet
    `note` qui se dit lecture de démonstration, puis les volets du type en ordre de date, et un volet
    illisible avant le dernier quand le Document est long."""
    pages = max(1, pages)
    volets: list[_Volet | None] = list(VOLETS.get(type_de_document, VOLETS["autre"]))
    if pages >= PAGES_POUR_UN_VOLET_ILLISIBLE:
        volets.insert(len(volets) - 1, None)
    etablissements = list(dict.fromkeys(v.etablissement for v in volets if v and v.etablissement))
    annees = sorted(v.date[:4] for v in volets if v and v.date)
    entete = ["---"]
    if etablissements:
        entete.append(f"etablissements: {'; '.join(etablissements)}")
    if annees:
        entete.append(f"periode: {annees[0]}" if annees[0] == annees[-1] else f"periode: {annees[0]}-{annees[-1]}")
    entete.append("---")
    morceaux = ["\n".join(entete), "\n".join([_titre("note", None, None, 1, 1), NOTE])]
    for volet, (debut, fin) in zip(volets, _tranches(pages, len(volets))):
        if volet is None:
            morceaux.append("\n".join([_titre("illisible", None, None, debut, fin), ILLISIBLE]))
        else:
            titre = _titre(volet.type, volet.date, volet.etablissement, debut, fin)
            morceaux.append("\n".join([titre, *volet.corps(debut, fin)]))
    return "\n\n".join(morceaux) + "\n"


def extraire(type_de_document: str, pages: int = 1) -> Extraction:
    """L'Extraction de démonstration d'un Document de ce type et de `pages` pages : un texte qui se dit
    exemple, un brouillon de Transcription qui renvoie à ces pages, et les propositions fixes du type ;
    aucune pour un type sans exemple (imagerie, certificat, autre)."""
    lignes, propositions = EXEMPLES.get(type_de_document, ([], []))
    return Extraction(
        modele=MODELE_DE_DEMONSTRATION,
        texte="\n".join([AVERTISSEMENT, "", *lignes]),
        transcription=transcription(type_de_document, pages),
        propositions=[p.model_copy(deep=True) for p in propositions],
    )
