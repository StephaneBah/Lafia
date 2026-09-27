"""Lire une Transcription (ADR 0010) : son en-tête, ses volets, les pages qu'ils citent.

Le Markdown d'une Transcription est écrit par la machine puis par les agents de relecture ; ce module
n'en rend rien en HTML (les applications ont leur propre rendu, restreint), il en tire la structure :
de quoi ordonner par date, regrouper par établissement, vérifier que chaque volet renvoie à des pages.
"""

import re
from dataclasses import dataclass, field

TYPES_DE_VOLET = (
    "consultation", "analyse", "ordonnance", "vaccination", "hospitalisation",
    "imagerie", "certificat", "note", "illisible", "autre",
)
INCONNU = "?"

# `## consultation · 2019-03-14 · CS Kpanroun · p. 3-4`
_TITRE = re.compile(
    r"^##\s+(?P<type>[^·\n]+?)\s*·\s*(?P<date>[^·\n]+?)\s*·\s*(?P<etablissement>[^·\n]+?)\s*·\s*p\.\s*(?P<pages>[0-9 ,\-–]+)\s*$"
)
_DATE = re.compile(r"^\d{4}(-\d{2}(-\d{2})?)?$")
_IMAGE = re.compile(r"!\[[^\]]*\]\(page:(\d+)(#[\d,]+)?\)")


@dataclass(frozen=True)
class Volet:
    titre: str
    type: str
    date: str | None
    """`AAAA`, `AAAA-MM` ou `AAAA-MM-JJ` ; None quand le papier ne la donne pas."""
    etablissement: str | None
    pages: tuple[int, ...]
    corps: str
    rang: int
    """La place du volet dans la Transcription, pour garder l'ordre des volets sans date."""


@dataclass(frozen=True)
class Transcription:
    etablissements: tuple[str, ...]
    periode: str | None
    volets: tuple[Volet, ...]
    erreurs: tuple[str, ...] = field(default=())
    """Ce qui ne suit pas le format : titres mal formés, pages hors du Document. Jamais bloquant pour lire ;
    une confirmation, elle, les refuse."""


def _pages(texte: str) -> tuple[int, ...]:
    pages: list[int] = []
    for morceau in re.split(r"\s*,\s*", texte.strip()):
        if not morceau:
            continue
        bornes = re.split(r"\s*[-–]\s*", morceau)
        if len(bornes) == 2 and bornes[0].isdigit() and bornes[1].isdigit():
            debut, fin = int(bornes[0]), int(bornes[1])
            pages.extend(range(min(debut, fin), max(debut, fin) + 1))
        elif morceau.isdigit():
            pages.append(int(morceau))
    return tuple(dict.fromkeys(pages))


def lire(markdown: str, pages_du_document: int | None = None) -> Transcription:
    """La structure d'une Transcription. `pages_du_document` permet de signaler les renvois hors du Document."""
    lignes = markdown.replace("\r\n", "\n").split("\n")
    etablissements: tuple[str, ...] = ()
    periode: str | None = None
    erreurs: list[str] = []
    debut = 0
    if lignes and lignes[0].strip() == "---":
        fin = next((i for i in range(1, len(lignes)) if lignes[i].strip() == "---"), None)
        if fin is not None:
            for ligne in lignes[1:fin]:
                cle, _, valeur = ligne.partition(":")
                if cle.strip() == "etablissements":
                    etablissements = tuple(e.strip() for e in valeur.split(";") if e.strip())
                elif cle.strip() == "periode":
                    periode = valeur.strip() or None
            debut = fin + 1
    volets: list[Volet] = []
    courant: dict[str, object] | None = None
    corps: list[str] = []

    def clore() -> None:
        if courant is not None:
            volets.append(Volet(corps="\n".join(corps).strip(), rang=len(volets), **courant))  # type: ignore[arg-type]

    for numero, ligne in enumerate(lignes[debut:], start=debut + 1):
        if ligne.startswith("## "):
            clore()
            corps = []
            trouve = _TITRE.match(ligne.strip())
            if not trouve:
                erreurs.append(f"ligne {numero} : titre de volet hors format")
                courant = {"titre": ligne[3:].strip(), "type": "autre", "date": None, "etablissement": None, "pages": ()}
                continue
            type_ = trouve["type"].strip().lower()
            date = trouve["date"].strip()
            etablissement = trouve["etablissement"].strip()
            pages = _pages(trouve["pages"])
            if type_ not in TYPES_DE_VOLET:
                erreurs.append(f"ligne {numero} : type de volet inconnu « {type_} »")
                type_ = "autre"
            if date != INCONNU and not _DATE.match(date):
                erreurs.append(f"ligne {numero} : date « {date} » hors format")
                date = INCONNU
            if pages_du_document and any(p < 1 or p > pages_du_document for p in pages):
                erreurs.append(f"ligne {numero} : page hors du document")
            courant = {
                "titre": ligne[3:].strip(),
                "type": type_,
                "date": None if date == INCONNU else date,
                "etablissement": None if etablissement == INCONNU else etablissement,
                "pages": pages,
            }
        elif courant is not None:
            corps.append(ligne)
            for image in _IMAGE.finditer(ligne):
                if pages_du_document and not 1 <= int(image.group(1)) <= pages_du_document:
                    erreurs.append(f"ligne {numero} : image d'une page hors du document")
    clore()
    return Transcription(etablissements=etablissements, periode=periode, volets=tuple(volets), erreurs=tuple(erreurs))


def par_date(volets: list[Volet]) -> list[Volet]:
    """Les volets en ordre de date ; un volet sans date garde sa place après le volet daté qui le précède."""
    ordonnes: list[Volet] = []
    derniere = ""
    cles: list[tuple[str, int, int]] = []
    for rang, volet in enumerate(volets):
        if volet.date:
            derniere = volet.date
        cles.append((volet.date or derniere, 0 if volet.date else 1, rang))
    for _, _, rang in sorted(cles):
        ordonnes.append(volets[rang])
    return ordonnes


def par_etablissement(volets: list[Volet]) -> dict[str, list[Volet]]:
    """Les volets regroupés par établissement (« Établissement non précisé » pour ceux sans), chacun en ordre de date."""
    groupes: dict[str, list[Volet]] = {}
    for volet in volets:
        groupes.setdefault(volet.etablissement or "Établissement non précisé", []).append(volet)
    return {nom: par_date(liste) for nom, liste in sorted(groupes.items())}
