"""Ce qu'un soignant envoie au service soin : les corps des requêtes, validés à l'entrée et passés
tels quels de la route (`soin.service`) au travail (`soin.dossier`)."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from commun.fhir.soin import LienDeParente, Moment

Npi = Annotated[str, StringConstraints(pattern=r"^\d{13}$")]
Texte = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
Periode = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class Recherche(BaseModel):
    npi: Npi


class NouveauCas(BaseModel):
    motif: Texte


class MesureSaisie(BaseModel):
    code: str
    valeur: float | str
    valeur2: float | None = None


class DiagnosticSaisi(BaseModel):
    code: str
    confirme: bool = False
    note: Annotated[str, StringConstraints(max_length=1000)] | None = None


class LigneSaisie(BaseModel):
    produit: str
    quantite: int = Field(ge=1)
    dose: float = Field(gt=0, default=1)
    moments: list[Moment] = []
    jours: int = Field(ge=1, default=1)


class NouvelleVisite(BaseModel):
    type: Literal["consultation", "soins-infirmiers", "continuite"]
    motif: Texte
    mesures: list[MesureSaisie] = []
    diagnostic: DiagnosticSaisi | None = None
    ordonnance: list[LigneSaisie] | None = None


class NouvelleAllergie(BaseModel):
    code_atc: Annotated[str, StringConstraints(pattern=r"^[A-Z][0-9]{2}[A-Z0-9]{0,4}$")]
    libelle: Texte | None = None
    """Facultatif : le libellé de la classe au catalogue des allergies fait foi."""


class DemandeDUrgence(BaseModel):
    raison: Annotated[str, StringConstraints(strip_whitespace=True, min_length=10, max_length=500)]


class NouvelAntecedent(BaseModel):
    type: Literal["medical", "chirurgical", "familial"]
    libelle: Texte
    depuis: Periode | None = None
    lien: LienDeParente | None = None
    actif: bool = True


class NouveauTraitement(BaseModel):
    produit: str | None = None
    libelle: Texte | None = None
    posologie: Texte
    moments: list[Moment] = []


class GroupeSanguin(BaseModel):
    valeur: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=5)]
