"""Qui le service relecture sert, et à quelle étape (ADR 0007, 0009, 0010).

Deux étages : l'agent de relecture fait la Relecture et le Contrôle des Transcriptions, et ne valide
aucun fait clinique ; le médecin et l'infirmier valident les propositions d'une Extraction. Tous passent
par la même application. Ni l'un ni l'autre ne voit qui est le patient : ni NPI, ni nom, ni lieu du
dépôt ; seules les pages peuvent en porter un.
"""

from commun.jeton import Agent, Role

RELECTEURS = frozenset({Role.AGENT_DE_RELECTURE})
SOIGNANTS = frozenset({Role.MEDECIN, Role.INFIRMIER})
ROLES_ADMIS = RELECTEURS | SOIGNANTS


def relit(agent: Agent) -> bool:
    """L'agent de relecture : Relectures et Contrôles."""
    return agent.role in RELECTEURS


def valide(agent: Agent) -> bool:
    return agent.role in SOIGNANTS


def confirme_un_diagnostic(agent: Agent) -> bool:
    """Seul un médecin confirme un antécédent ou une allergie lus par une Extraction ; ceux qu'un
    infirmier accepte restent à confirmer, comme ses diagnostics de visite."""
    return agent.role is Role.MEDECIN
