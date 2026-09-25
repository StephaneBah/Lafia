// Le service soin, vu du serveur de l'application. Il n'est joint que par la passerelle :
// l'application n'est pas sur le réseau du noyau et ne parle jamais FHIR.

const DELAI_MS = 5000;

/** Cookie de session de l'application, celui que les services lisent (`commun.jeton.COOKIE_DE_SESSION`). */
export const COOKIE_DE_SESSION = "__Host-session";

/** Réponse de `GET /api/soin/sante`, telle que le service la définit. */
export type Sante = {
  service: string;
  statut: "disponible" | "indisponible";
  noyau: {
    statut: "disponible" | "injoignable";
    version_fhir: string | null;
  };
};

/** Réponse de `GET /api/soin/session` : le soignant connecté, tel que le service lit son jeton vérifié. */
export type Session = {
  sub: string;
  role: "médecin" | "infirmier";
  etablissement: string;
};

/** Adresse interne de la passerelle pour le sous-domaine soin, lue dans `PASSERELLE_URL`. */
function adressePasserelle(): string {
  const adresse = process.env.PASSERELLE_URL;
  if (!adresse) {
    throw new Error("PASSERELLE_URL manquante : adresse interne de la passerelle pour soin.");
  }
  return adresse;
}

/**
 * Demande `chemin` au service soin, par la passerelle. Rend le corps JSON quand le service répond
 * par l'un des `statutsAttendus` ; `null` pour tout autre statut, ou quand il ne répond pas.
 */
async function demander<T>(
  chemin: string,
  statutsAttendus: number[],
  enTetes: HeadersInit = {},
): Promise<T | null> {
  const adresse = `${adressePasserelle()}${chemin}`;
  try {
    const reponse = await fetch(adresse, {
      cache: "no-store",
      headers: enTetes,
      signal: AbortSignal.timeout(DELAI_MS),
    });
    if (!statutsAttendus.includes(reponse.status)) {
      console.warn(`service soin : ${adresse} a répondu ${reponse.status}`);
      return null;
    }
    return (await reponse.json()) as T;
  } catch (erreur) {
    console.warn(`service soin injoignable : ${adresse}`, erreur);
    return null;
  }
}

/** État du service soin et du noyau derrière lui ; `null` quand le service ne répond pas. */
export function lireSante(): Promise<Sante | null> {
  // 200 : toute la chaîne répond. 503 : le service répond, le noyau non. Les deux décrivent l'état.
  return demander<Sante>("/api/soin/sante", [200, 503]);
}

/**
 * Le soignant que désigne le jeton de session, vérifié par le service : l'application ne lit pas le
 * jeton elle-même. `null` quand le service le refuse (401, 403) ou ne répond pas.
 */
export function lireSession(jeton: string): Promise<Session | null> {
  return demander<Session>("/api/soin/session", [200], { Cookie: `${COOKIE_DE_SESSION}=${jeton}` });
}
