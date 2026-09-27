// Dans le navigateur : quand le jeton a expiré entre deux enregistrements, le serveur de l'application
// le renouvelle au prochain chargement d'une page (proxy.ts). On recharge donc la page en arrière-plan,
// sans quitter l'écran, puis on refait l'appel une fois.

async function renouvelerLaSession(): Promise<void> {
  try {
    await fetch(window.location.href, { cache: "no-store", credentials: "same-origin" });
  } catch {
    // Hors ligne : l'appel suivant le dira.
  }
}

export async function avecSession<T extends { ok: boolean }>(appel: () => Promise<T>): Promise<T> {
  const premier = await appel();
  if (premier.ok || (premier as { statut?: number }).statut !== 401) return premier;
  await renouvelerLaSession();
  return appel();
}

/** Pourquoi une action n'est pas passée, en mots, d'après le statut du service. */
export function motDuRefus(statut: number): string {
  if (statut === 0 || statut >= 500) return "Le service relecture ne répond pas. Rien n'est perdu : réessayez dans un instant.";
  if (statut === 401) return "Votre session a pris fin. Ouvrez la connexion dans un autre onglet, puis réessayez : ce qui est à l'écran reste.";
  if (statut === 403) return "Cette tâche ne vous est pas confiée, ou n'est pas à cette étape.";
  if (statut === 404) return "Cette tâche n'existe plus.";
  if (statut === 409) return "La tâche a changé depuis que vous l'avez ouverte : elle a pu être faite ailleurs.";
  return "Le service a refusé cette demande.";
}

/** Où aller après une tâche faite. */
export function adresseDeLaSuite(suivante: string | null, fait: string): string {
  return suivante ? `/taches/${encodeURIComponent(suivante)}?fait=${fait}` : `/?fait=${fait}`;
}
