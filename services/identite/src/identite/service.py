"""Service identite : ses routes sous /api/identite. Il ne parle jamais FHIR et n'est pas sur le réseau du noyau."""

from commun.service import creer_service

SERVICE = "identite"

app = creer_service(SERVICE, parle_fhir=False)
