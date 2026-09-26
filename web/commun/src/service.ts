// Le service d'une application, et identite, vus du serveur de l'application. Ils ne sont joints que
// par la passerelle, à l'entrée interne du sous-domaine de l'application : l'application n'est pas sur
// le réseau du noyau et ne parle jamais FHIR.

export const DELAI_MS = 5000;

/** Cookie du jeton de chaque application, celui que les services lisent (`commun.jeton.COOKIE_DE_SESSION`). */
export const COOKIE_DE_SESSION = "__Host-session";

/** Cookie de la session qui renouvelle le jeton ; seul identite le lit. */
export const COOKIE_DE_RENOUVELLEMENT = "__Host-renouvellement";

/** Réponse de `GET /api/<service>/sante` d'un service qui parle FHIR (`commun.service.Sante`). */
export type Sante = {
  service: string;
  statut: "disponible" | "indisponible";
  noyau: {
    statut: "disponible" | "injoignable";
    version_fhir: string | null;
  };
};

/** Le rôle d'un agent, professionnel rattaché à un établissement (`commun.jeton.Role`). */
export type RoleAgent = "médecin" | "infirmier" | "caissier" | "pharmacien";

/** Un agent connecté, tel que `GET /api/identite/session` le rend : de quoi le nommer, lui et son établissement. */
export type SessionAgent = {
  sub: string;
  role: RoleAgent;
  etablissement: string;
  nom: string;
  nom_etablissement: string;
};

/** Une officine connectée : son nom ; elle n'est pas un établissement. */
export type SessionOfficine = {
  sub: string;
  role: "officine";
  nom: string;
};

/** Le citoyen connecté, sans son NPI, que ni identite ni son service ne renvoient jamais. */
export type SessionCitoyen = {
  sub: string;
  role: "citoyen";
};

/** Qui est connecté, selon identite : un agent, une officine ou le citoyen. Le rôle les distingue. */
export type Session = SessionAgent | SessionOfficine | SessionCitoyen;

/** Un compte de démonstration d'agent ou d'officine, que la page de connexion liste (mot de passe public). */
export type CompteDeDemonstration = {
  identifiant: string;
  mot_de_passe: string;
  role: RoleAgent | "officine";
  /** Le nom de l'établissement de l'agent, ou celui de l'officine. */
  structure: string;
};

/** Un citoyen de démonstration, que la page de connexion du citoyen liste. */
export type CitoyenDeDemonstration = {
  npi: string;
  code: string;
  role: "citoyen";
};

/** Adresse interne de la passerelle pour le sous-domaine de l'application, lue dans `PASSERELLE_URL`. */
export function adressePasserelle(): string {
  const adresse = process.env.PASSERELLE_URL;
  if (!adresse) {
    throw new Error("PASSERELLE_URL manquante : adresse interne de la passerelle pour cette application.");
  }
  return adresse;
}

/**
 * Demande `chemin` par la passerelle. Rend le corps JSON quand le service répond par l'un des
 * `statutsAttendus` ; `null` pour tout autre statut, ou quand il ne répond pas.
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

/** Ce qu'une application demande à son service. */
export type Service = {
  /** État du service et du noyau derrière lui ; `null` quand le service ne répond pas. */
  lireSante(): Promise<Sante | null>;
};

/** Le service `service` (soin, caisse, …), joint sous `/api/<service>` par la passerelle. */
export function serviceParLaPasserelle(service: string): Service {
  return {
    // 200 : toute la chaîne répond. 503 : le service répond, le noyau non. Les deux décrivent l'état.
    lireSante: () => demander<Sante>(service, `/api/${service}/sante`, [200, 503]),
  };
}

/** Ce qu'une application demande à identite. */
export type Identite = {
  /**
   * Le porteur du jeton de session, vérifié par identite : l'application ne lit pas le jeton
   * elle-même. `null` quand identite le refuse ou ne répond pas.
   */
  lireSession(jeton: string): Promise<Session | null>;
  /** Les comptes de démonstration des rôles que l'application connecte ; `null` quand identite ne répond pas. */
  lireComptesDeDemonstration(): Promise<(CompteDeDemonstration | CitoyenDeDemonstration)[] | null>;
};

/** identite, joint sous `/api/identite` par la passerelle, sur le sous-domaine de l'application. */
export function identiteParLaPasserelle(): Identite {
  return {
    lireSession: (jeton) =>
      demander<Session>("identite", "/api/identite/session", [200], {
        Cookie: `${COOKIE_DE_SESSION}=${jeton}`,
      }),
    lireComptesDeDemonstration: () =>
      demander<(CompteDeDemonstration | CitoyenDeDemonstration)[]>(
        "identite",
        "/api/identite/comptes-de-demonstration",
        [200],
      ),
  };
}
