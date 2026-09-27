// Le service relecture et identite, vus du serveur de l'application : joints par la passerelle, avec
// le jeton de session du relecteur, que le navigateur a porté jusqu'ici dans son cookie. Rien de ce que
// le service rend ne nomme le patient : ni NPI, ni nom (docs/specs/F6-relecture-et-extraction.md).
import { COOKIE_DE_SESSION } from "@lafia/commun";
import { cookies } from "next/headers";

const DELAI_MS = 5000;

/** Les rôles qui ouvrent la relecture : le triage pour l'agent de relecture, la validation pour un soignant. */
const ROLES_ADMIS = new Set(["agent de relecture", "agent-relecture", "médecin", "infirmier"]);

/** Le relecteur connecté, tel que identite le nomme. */
export type Relecteur = {
  sub: string;
  role: string;
  nom: string;
  etablissement: string;
  nom_etablissement: string;
};

export type Etape = "triage" | "validation";

/** Ce que le relecteur voit du Document : ce que l'agent de numérisation a déclaré, jamais à qui il est. */
export type DocumentARelire = { type: string; annee: string | number; pages: number; lisibilite?: string };

/** Une ligne de « Ma semaine ». Un `verdict` présent : la tâche est faite. */
export type Tache = {
  id: string;
  etape: Etape;
  document: DocumentARelire;
  echeance: string;
  verdict?: string | null;
};

/** Un fait que la machine propose, à accepter, corriger ou rejeter. */
export type Proposition = {
  id: string;
  type: string;
  libelle: string;
  valeur: string;
  confiance: number;
  extrait?: string;
};

export type Modele = { nom: string; version: string };

export type TacheDetaillee = Tache & {
  propositions?: Proposition[];
  modele?: Modele;
  texte?: string;
};

export type Verdict = "utilisable" | "illisible" | "non-medical" | "mauvais-type" | "doublon";

export type Decision = { id: string; decision: "accepter" | "corriger" | "rejeter"; valeur?: string };

/** Ce que rend un appel : le corps quand le statut est attendu, sinon le statut seul (0 : injoignable). */
export type Reponse<T> = { ok: true; corps: T } | { ok: false; statut: number };

async function appeler<T>(chemin: string, attendus: number[], init: RequestInit = {}): Promise<Reponse<T>> {
  const passerelle = process.env.PASSERELLE_URL;
  const porte = (await cookies()).get(COOKIE_DE_SESSION)?.value;
  if (!passerelle) throw new Error("PASSERELLE_URL manquante : adresse interne de la passerelle pour cette application.");
  if (!porte) return { ok: false, statut: 401 };
  try {
    const reponse = await fetch(`${passerelle}${chemin}`, {
      ...init,
      cache: "no-store",
      headers: { ...init.headers, Cookie: `${COOKIE_DE_SESSION}=${porte}` },
      signal: AbortSignal.timeout(DELAI_MS),
    });
    if (!attendus.includes(reponse.status)) return { ok: false, statut: reponse.status };
    const texte = await reponse.text();
    return { ok: true, corps: (texte ? JSON.parse(texte) : null) as T };
  } catch {
    // Seulement le fait : le journal ne cite ni la tâche ni ce qu'elle contient.
    console.warn("relecture : service injoignable");
    return { ok: false, statut: 0 };
  }
}

/** Le relecteur connecté, ou `null` sans session valide (ou pour un rôle qui ne relit pas). */
export async function lireRelecteur(): Promise<Relecteur | null> {
  const reponse = await appeler<Relecteur>("/api/identite/session", [200]);
  return reponse.ok && ROLES_ADMIS.has(reponse.corps.role) ? reponse.corps : null;
}

/** L'agent de relecture trie ; le médecin et l'infirmier valident. */
export function estSoignant(relecteur: Relecteur): boolean {
  return relecteur.role === "médecin" || relecteur.role === "infirmier";
}

function adresseDeLaTache(tache: string): string {
  return `/api/relecture/taches/${encodeURIComponent(tache)}`;
}

/** Les tâches de la semaine en cours du relecteur connecté. */
export function lireMaSemaine(): Promise<Reponse<Tache[]>> {
  return appeler<Tache[]>("/api/relecture/taches", [200]);
}

export function lireTache(tache: string): Promise<Reponse<TacheDetaillee>> {
  return appeler<TacheDetaillee>(adresseDeLaTache(tache), [200]);
}

export function trier(tache: string, corps: { verdict: Verdict; type?: string; annee?: number }): Promise<Reponse<unknown>> {
  return appeler<unknown>(`${adresseDeLaTache(tache)}/triage`, [200, 201, 204], {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(corps),
  });
}

export function valider(tache: string, propositions: Decision[]): Promise<Reponse<unknown>> {
  return appeler<unknown>(`${adresseDeLaTache(tache)}/validation`, [200, 201, 204], {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ propositions }),
  });
}

/** Une tâche reste à faire tant qu'elle n'a pas de verdict. */
export function estFaite(tache: Tache): boolean {
  return Boolean(tache.verdict);
}

/** La prochaine tâche à faire de la semaine, autre que celle qu'on quitte ; `null` quand tout est fait. */
export async function tacheSuivante(sauf?: string): Promise<string | null> {
  const semaine = await lireMaSemaine();
  if (!semaine.ok) return null;
  return semaine.corps.find((tache) => !estFaite(tache) && tache.id !== sauf)?.id ?? null;
}
