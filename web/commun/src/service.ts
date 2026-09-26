// Le service d'une application, vu du serveur de l'application. Il n'est joint que par la passerelle,
// à l'entrée interne du sous-domaine de l'application : l'application n'est pas sur le réseau du
// noyau et ne parle jamais FHIR.

const DELAI_MS = 5000;

/** Cookie de session de chaque application, celui que les services lisent (`commun.jeton.COOKIE_DE_SESSION`). */
export const COOKIE_DE_SESSION = "__Host-session";

/** Réponse de `GET /api/<service>/sante` d'un service qui parle FHIR (`commun.service.Sante`). */
export type Sante = {
  service: string;
  statut: "disponible" | "indisponible";
  noyau: {
    statut: "disponible" | "injoignable";
    version_fhir: string | null;
  };
};

/** Le rôle d'un agent, professionnel rattaché à un établissement (`commun.jeton.Role`, sans citoyen). */
export type RoleAgent = "médecin" | "infirmier" | "caissier" | "pharmacien";

/** Réponse de `GET /api/<service>/session` d'un service d'agents : l'agent, tel que le service lit son jeton vérifié. */
export type SessionAgent = {
  sub: string;
  role: RoleAgent;
  etablissement: string;
};

/** Réponse de `GET /api/citoyen/session` : le citoyen, sans son NPI, que le service ne renvoie jamais. */
export type SessionCitoyen = {
  sub: string;
  role: "citoyen";
};

/** Qui est connecté, selon le service : un agent, ou le citoyen. Le rôle les distingue. */
export type Session = SessionAgent | SessionCitoyen;

/** Ce qu'une application demande à son service. */
export type Service = {
  /** État du service et du noyau derrière lui ; `null` quand le service ne répond pas. */
  lireSante(): Promise<Sante | null>;
  /**
   * L'agent ou le citoyen que désigne le jeton de session, vérifié par le service : l'application ne
   * lit pas le jeton elle-même. `null` quand le service le refuse (401, 403) ou ne répond pas.
   */
  lireSession(jeton: string): Promise<Session | null>;
};

/** Adresse interne de la passerelle pour le sous-domaine de l'application, lue dans `PASSERELLE_URL`. */
function adressePasserelle(): string {
  const adresse = process.env.PASSERELLE_URL;
  if (!adresse) {
    throw new Error("PASSERELLE_URL manquante : adresse interne de la passerelle pour cette application.");
  }
  return adresse;
}

/**
 * Demande `chemin` au service, par la passerelle. Rend le corps JSON quand le service répond par
 * l'un des `statutsAttendus` ; `null` pour tout autre statut, ou quand il ne répond pas.
 */
async function demander<T>(
  service: string,
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
      console.warn(`service ${service} : ${adresse} a répondu ${reponse.status}`);
      return null;
    }
    return (await reponse.json()) as T;
  } catch (erreur) {
    console.warn(`service ${service} injoignable : ${adresse}`, erreur);
    return null;
  }
}

/** Le service `service` (soin, caisse, …), joint sous `/api/<service>` par la passerelle. */
export function serviceParLaPasserelle(service: string): Service {
  return {
    // 200 : toute la chaîne répond. 503 : le service répond, le noyau non. Les deux décrivent l'état.
    lireSante: () => demander<Sante>(service, `/api/${service}/sante`, [200, 503]),
    lireSession: (jeton) =>
      demander<Session>(service, `/api/${service}/session`, [200], {
        Cookie: `${COOKIE_DE_SESSION}=${jeton}`,
      }),
  };
}
