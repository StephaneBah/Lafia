"""Service extraction : `POST /api/extraction/extraire`, et /sante. Interne (ADR 0009).

Il n'est sur aucun réseau que la passerelle atteint, ni sur celui du noyau : seul le service `relecture`
le joint, sur le réseau `extraction`. Aucune route de la passerelle n'y mène, aucune application ne
l'appelle, et il ne vérifie donc aucun jeton : le réseau est sa garde. Il ne garde rien : ni pages, ni
texte, ni propositions. Ses journaux ne portent que l'identifiant du Document, le nombre de pages et la
durée : jamais une page, un texte ni un fait.
"""

import logging
import time

from fastapi import APIRouter

from commun.extraction import DemandeDExtraction, Extraction
from commun.service import creer_service
from extraction.regles import demonstration

SERVICE = "extraction"

journal = logging.getLogger(SERVICE)

routes = APIRouter()


@routes.post("/extraire")
async def extraire(demande: DemandeDExtraction) -> Extraction:
    """Lit les pages d'un Document : son texte, un brouillon de Transcription en volets (ADR 0010) qui
    renvoie à ces pages, et les faits proposés, chacun avec sa confiance. Le modèle
    et sa version sont nommés : aujourd'hui `demonstration:0`, l'Extraction de démonstration."""
    debut = time.perf_counter()
    extraction = demonstration.extraire(demande.type_de_document, len(demande.pages))
    journal.info(
        "document %s lu : %d pages, %d propositions, modèle %s:%s, %.0f ms",
        demande.document_id,
        len(demande.pages),
        len(extraction.propositions),
        extraction.modele.nom,
        extraction.modele.version,
        (time.perf_counter() - debut) * 1000,
    )
    return extraction


app = creer_service(SERVICE, routes, parle_fhir=False)
