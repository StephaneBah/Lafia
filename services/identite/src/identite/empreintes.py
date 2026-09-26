"""Les empreintes des secrets qu'identite garde : aucun n'est écrit en clair, et une copie de sa base
n'ouvre rien.

- Mots de passe et codes carnet : argon2id, lent exprès, aux paramètres minimaux que recommande
  l'OWASP (19 Mio, deux passes, un fil) : assez pour décourager la devinette hors ligne, assez peu pour
  tenir dans la mémoire du conteneur. Le calcul tourne hors de la boucle d'événements.
- Identifiants de session et clés des compteurs d'échecs : SHA-256. Un identifiant de session est
  aléatoire et long, rien à deviner ; une clé de compteur n'a pas à être lisible, puisqu'elle peut
  porter un NPI ou un mot de passe tapé à la place de l'identifiant.
"""

import asyncio
import hashlib

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_argon2 = PasswordHasher(time_cost=2, memory_cost=19 * 1024, parallelism=1)

# Vérifiée quand l'identifiant ou le NPI n'a pas d'empreinte : le refus prend alors le temps d'un
# mauvais mot de passe, et ne dit pas si le compte existe.
_EMPREINTE_FACTICE = _argon2.hash("aucun secret ne donne cette empreinte")


async def hacher(secret: str) -> str:
    """L'empreinte argon2id d'un mot de passe ou d'un code carnet."""
    return await asyncio.to_thread(_argon2.hash, secret)


async def verifier(empreinte: str | None, secret: str) -> bool:
    """Si `secret` donne `empreinte`. Sans empreinte, le même calcul, pour un refus."""
    try:
        concorde = await asyncio.to_thread(_argon2.verify, empreinte or _EMPREINTE_FACTICE, secret)
    except (VerificationError, InvalidHashError):
        return False
    return concorde and empreinte is not None


def empreinte_rapide(texte: str) -> bytes:
    """L'empreinte SHA-256 d'un identifiant de session ou d'une clé de compteur."""
    return hashlib.sha256(texte.encode()).digest()
