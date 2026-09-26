"""Émission des jetons de session : identite seul tient la clé privée qui les signe (ADR 0004).

Leurs revendications et leur durée de vie viennent de `commun.jeton`, que les services lisent pour
les vérifier. identite vérifie les siens avec la moitié publique de sa clé.
"""

from datetime import datetime

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import load_der_private_key

from commun.jeton import ALGORITHME, Porteur, VerificateurDeJetons, lire_cle, revendications

# Clé privée de la paire de développement. Elle n'a rien de secret : tests/conftest.py la tient aussi,
# pour forger des jetons mal formés. `lire_cle` ne la prend que sur localhost, et la refuse ailleurs.
CLE_PRIVEE_DE_DEVELOPPEMENT = "MC4CAQAwBQYDK2VwBCIEINp8yVHhQe5B/gcbA5wNMNwe0d+oaAY7090L95AC8EvZ"


class SignataireDeJetons:
    def __init__(self, cle_privee: Ed25519PrivateKey) -> None:
        self._cle_privee = cle_privee

    @classmethod
    def depuis_environnement(cls) -> "SignataireDeJetons":
        """Clé privée lue dans `JETON_CLE_PRIVEE`, par la règle de `commun.jeton.lire_cle`."""
        try:
            cle = load_der_private_key(lire_cle("JETON_CLE_PRIVEE", CLE_PRIVEE_DE_DEVELOPPEMENT), password=None)
        except ValueError as erreur:
            raise RuntimeError("JETON_CLE_PRIVEE illisible : clé privée DER.") from erreur
        if not isinstance(cle, Ed25519PrivateKey):
            raise RuntimeError("JETON_CLE_PRIVEE n'est pas une clé privée Ed25519.")
        return cls(cle)

    def signer(self, porteur: Porteur, expiration: datetime) -> str:
        """Le jeton de `porteur`, qui expire à `expiration`."""
        return jwt.encode({**revendications(porteur), "exp": expiration}, self._cle_privee, algorithm=ALGORITHME)

    def verificateur(self) -> VerificateurDeJetons:
        """Le vérificateur des jetons que ce signataire émet."""
        return VerificateurDeJetons(self._cle_privee.public_key())
