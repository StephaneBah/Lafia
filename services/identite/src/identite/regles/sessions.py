"""Combien de temps dure une session (ADR 0004).

Un agent ou une officine garde sa session le temps d'une garde, 12 heures au plus, tant qu'elle ne
reste pas 30 minutes sans renouvellement : un poste partagé ne reste pas ouvert sous son nom. Le
citoyen garde la sienne une heure au plus : un téléphone partagé en famille ne garde pas son carnet
ouvert. Un renouvellement compte comme une activité. Un jeton vit 15 minutes, jamais au-delà de sa session.
"""

from datetime import datetime, timedelta

from commun.jeton import DUREE_DE_VIE, Role

DUREE_MAXIMALE_D_UN_AGENT = timedelta(hours=12)
INACTIVITE_MAXIMALE_D_UN_AGENT = timedelta(minutes=30)
DUREE_MAXIMALE_D_UN_CITOYEN = timedelta(hours=1)


def fin_de_session(role: Role, debut: datetime, derniere_activite: datetime) -> datetime:
    """Quand prend fin la session ouverte à `debut`, et renouvelée pour la dernière fois à `derniere_activite`."""
    if role is Role.CITOYEN:
        return debut + DUREE_MAXIMALE_D_UN_CITOYEN
    return min(debut + DUREE_MAXIMALE_D_UN_AGENT, derniere_activite + INACTIVITE_MAXIMALE_D_UN_AGENT)


def expiration_du_jeton(maintenant: datetime, fin_de_session: datetime) -> datetime:
    """Quand expire un jeton émis `maintenant` par une session qui prend fin à `fin_de_session`."""
    return min(maintenant + DUREE_DE_VIE, fin_de_session)
