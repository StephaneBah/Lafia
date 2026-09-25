// Le service soin, vu du serveur de l'application. Il n'est joint que par la passerelle :
// l'application n'est pas sur le réseau du noyau et ne parle jamais FHIR.

const DELAI_MS = 5000;

/** Réponse de `GET /api/soin/sante`, telle que le service la définit. */
export type Sante = {
  service: string;
  statut: "disponible" | "indisponible";
  noyau: {
    statut: "disponible" | "injoignable";
    version_fhir: string | null;
  };
};

/** Adresse interne de la passerelle pour le sous-domaine soin, lue dans `PASSERELLE_URL`. */
function adressePasserelle(): string {
  const adresse = process.env.PASSERELLE_URL;
  if (!adresse) {
    throw new Error("PASSERELLE_URL manquante : adresse interne de la passerelle pour soin.");
  }
  return adresse;
}

/** État du service soin et du noyau derrière lui ; `null` quand le service ne répond pas. */
export async function lireSante(): Promise<Sante | null> {
  const adresse = `${adressePasserelle()}/api/soin/sante`;
  try {
    const reponse = await fetch(adresse, {
      cache: "no-store",
      signal: AbortSignal.timeout(DELAI_MS),
    });
    // 200 : toute la chaîne répond. 503 : le service répond, le noyau non. Les deux décrivent l'état.
    if (reponse.status !== 200 && reponse.status !== 503) {
      console.warn(`service soin : ${adresse} a répondu ${reponse.status}`);
      return null;
    }
    return (await reponse.json()) as Sante;
  } catch (erreur) {
    console.warn(`service soin injoignable : ${adresse}`, erreur);
    return null;
  }
}
