"""Chargement du jeu de démonstration dans le noyau : `python -m donnees.chargement`.

Une seule transaction de PUT, chaque ressource sous son identifiant fixe : tout le jeu est écrit, ou
rien. Rejoué à chaque démarrage de la pile, il ne supprime jamais rien : une ressource inchangée garde
sa version ; une ressource du jeu modifiée, dans le jeu ou par un utilisateur, reprend le contenu du jeu
en une nouvelle version, l'ancienne restant dans son historique ; ce que les utilisateurs ont créé
reste. Adresse du noyau lue dans `NOYAU_URL`.
"""

import asyncio
import logging
from collections import Counter

import donnees
from commun.fhir.client import ClientFhir, Ressource, ecriture
from commun.fhir.ressources import charge_item_definition, organization, patient, practitioner

journal = logging.getLogger("donnees.chargement")


def ressources() -> list[Ressource]:
    """Tout le jeu, traduit en ressources FHIR."""
    return [
        *(organization(etablissement) for etablissement in donnees.etablissements()),
        *(organization(officine) for officine in donnees.officines()),
        *(practitioner(agent) for agent in donnees.agents()),
        *(patient(personne) for personne in donnees.patients()),
        *(charge_item_definition(tarif) for tarif in donnees.tarifs()),
    ]


async def charger() -> None:
    fhir = ClientFhir.depuis_environnement()
    try:
        statuts = Counter(await fhir.transaction([ecriture(ressource) for ressource in ressources()]))
    finally:
        await fhir.fermer()
    # 201 : créée à ce chargement. 200 : déjà là, mise à jour si le jeu a changé, sinon laissée telle quelle.
    journal.info(
        "jeu de démonstration chargé : %d ressources, %d créées, %d déjà présentes",
        statuts.total(),
        statuts[201],
        statuts[200],
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(name)s : %(message)s")
    journal.setLevel(logging.INFO)
    asyncio.run(charger())
