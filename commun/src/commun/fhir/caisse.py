"""La caisse dans le noyau : les lignes d'une ordonnance, leurs tarifs, et l'encaissement en `Invoice`.

Formes : docs/specs/F3-v1-complete.md, contrat FHIR. Une ligne est payée quand un `Invoice` porte son
identifiant dans un `lineItem` ; le tarif d'un produit à un établissement est le `ChargeItemDefinition`
`tarif-<établissement>-<code>`.
"""

from typing import Any

from commun.fhir import systemes
from commun.fhir.client import ClientFhir, Ressource
from commun.fhir.dossier import id_de, maintenant, reference
from commun.fhir.ressources import DEVISE

# Une ligne annulée ou saisie par erreur n'est pas à payer.
STATUTS_ECARTES = {"cancelled", "entered-in-error", "stopped"}


async def lignes_de_l_ordonnance(fhir: ClientFhir, numero: str) -> list[Ressource]:
    """Les `MedicationRequest` dont le `groupIdentifier` porte ce numéro d'ordonnance, dans leur ordre d'écriture."""
    lignes = await fhir.chercher("MedicationRequest", {"identifier": f"{systemes.ORDONNANCE}|{numero}"})
    # Le noyau numérote ce qu'il crée dans l'ordre : `9` avant `10`.
    lignes.sort(key=lambda ligne: (len(ligne["id"]), ligne["id"]))
    return [ligne for ligne in lignes if ligne.get("status") not in STATUTS_ECARTES]


def etablissement_de_la_ligne(ligne: Ressource) -> str | None:
    """L'établissement où la ligne se paie et se remet : `dispenseRequest.performer`."""
    return id_de(ligne.get("dispenseRequest", {}).get("performer"))


def code_du_produit(ligne: Ressource) -> str | None:
    """Le code catalogue du produit ou de l'acte de la ligne : `MED-PARACETAMOL-500`."""
    codes = ligne.get("medicationCodeableConcept", {}).get("coding", [])
    return next((c.get("code") for c in codes if c.get("system") == systemes.CATALOGUE), None)


def libelle_du_produit(ligne: Ressource) -> str:
    concept = ligne.get("medicationCodeableConcept", {})
    if concept.get("text"):
        return str(concept["text"])
    codes = concept.get("coding", [])
    return next((str(c["display"]) for c in codes if c.get("display")), code_du_produit(ligne) or "")


def quantite(ligne: Ressource) -> int:
    """La quantité prescrite, en unités du tarif (comprimés, actes)."""
    valeur = ligne.get("dispenseRequest", {}).get("quantity", {}).get("value", 1)
    return int(valeur)


async def prix_unitaire(fhir: ClientFhir, etablissement: str, code: str) -> int | None:
    """Le tarif du produit `code` à l'établissement, en FCFA ; None quand il n'en a pas."""
    tarif = await fhir.lire("ChargeItemDefinition", f"tarif-{etablissement}-{code}".lower())
    if not tarif:
        return None
    for groupe in tarif.get("propertyGroup", []):
        for composante in groupe.get("priceComponent", []):
            if composante.get("type") == "base":
                return int(composante["amount"]["value"])
    return None


async def encaissements(fhir: ClientFhir, numero: str) -> list[Ressource]:
    """Les `Invoice` déjà écrits pour cette ordonnance."""
    return await fhir.chercher("Invoice", {"identifier": f"{systemes.ORDONNANCE}|{numero}"})


async def encaissement_par_recepisse(fhir: ClientFhir, recepisse: str) -> Ressource | None:
    trouves = await fhir.chercher("Invoice", {"identifier": f"{systemes.RECEPISSE}|{recepisse}"})
    return trouves[0] if trouves else None


def lignes_encaissees(invoice: Ressource) -> list[tuple[str, str, int]]:
    """Les lignes d'un encaissement : identifiant du MedicationRequest, libellé, montant payé."""
    lignes = []
    for item in invoice.get("lineItem", []):
        concept = item.get("chargeItemCodeableConcept", {})
        code = next((c.get("code") for c in concept.get("coding", []) if c.get("system") == systemes.LIGNE), None)
        if not code:
            continue
        montant = next(
            (int(p["amount"]["value"]) for p in item.get("priceComponent", []) if p.get("type") == "base"), 0
        )
        lignes.append((code, str(concept.get("text", "")), montant))
    return lignes


def lignes_payees(factures: list[Ressource]) -> set[str]:
    """Les identifiants des lignes que portent ces encaissements."""
    return {id_ for facture in factures for id_, _, _ in lignes_encaissees(facture)}


def identifiant(ressource: Ressource, systeme: str) -> str | None:
    return next((i.get("value") for i in ressource.get("identifier", []) if i.get("system") == systeme), None)


def nom_affiche(ressource: Ressource | None) -> tuple[str, str]:
    """Nom et prénoms du premier `name` d'un Patient ou d'un Practitioner."""
    if not ressource or not ressource.get("name"):
        return "", ""
    nom: dict[str, Any] = ressource["name"][0]
    return str(nom.get("family", "")), " ".join(nom.get("given", []))


def invoice(
    *,
    recepisse: str,
    numero: str,
    patient: str,
    etablissement: str,
    caissier: str,
    lignes: list[tuple[str, str, int]],
) -> Ressource:
    """Un encaissement, en `Invoice` : `lignes` sont (identifiant du MedicationRequest, libellé, montant)."""
    return {
        "resourceType": "Invoice",
        "status": "balanced",
        "identifier": [
            {"system": systemes.RECEPISSE, "value": recepisse},
            {"system": systemes.ORDONNANCE, "value": numero},
        ],
        "subject": reference("Patient", patient),
        "issuer": reference("Organization", etablissement),
        "participant": [{"actor": reference("Practitioner", caissier)}],
        "date": maintenant(),
        "lineItem": [
            {
                "sequence": rang,
                "chargeItemCodeableConcept": {
                    "coding": [{"system": systemes.LIGNE, "code": id_, "display": libelle}],
                    "text": libelle,
                },
                "priceComponent": [{"type": "base", "amount": {"value": montant, "currency": DEVISE}}],
            }
            for rang, (id_, libelle, montant) in enumerate(lignes, start=1)
        ],
        "totalGross": {"value": sum(montant for _, _, montant in lignes), "currency": DEVISE},
    }


async def lignes_vendues_en_officine(fhir: ClientFhir, lignes: list[Ressource]) -> set[str]:
    """Les lignes qu'une officine a déjà vendues : une délivrance sans encaissement ici. La caisse ne les
    encaisse plus, le patient les a réglées dans l'officine."""
    if not lignes:
        return set()
    delivrances = await fhir.chercher(
        "MedicationDispense", {"prescription": ",".join(f"MedicationRequest/{ligne['id']}" for ligne in lignes)}
    )
    vendues: set[str] = set()
    for delivrance in delivrances:
        if not any(p.get("actor", {}).get("reference", "").startswith("Practitioner/") for p in delivrance.get("performer", [])):
            vendues.update(ref["reference"].rsplit("/", 1)[-1] for ref in delivrance.get("authorizingPrescription", []))
    return vendues
