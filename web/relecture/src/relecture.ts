// Le service relecture et identite, vus du serveur de l'application : joints par la passerelle, avec
// le jeton de session du relecteur, que le navigateur a porté jusqu'ici dans son cookie. Rien de ce que
// le service rend ne nomme le patient : ni NPI, ni nom (docs/specs/F6-relecture-et-extraction.md).
import { COOKIE_DE_SESSION } from "@lafia/commun";
import { cookies } from "next/headers";

import type { Etape, Tache, TacheDetaillee } from "./types";

export type * from "./types";

const DELAI_MS = 8000;

/** Les rôles qui ouvrent la relecture : Relecture et Contrôle pour l'agent de relecture, validation pour un soignant. */
const ROLES_ADMIS = new Set(["agent de relecture", "médecin", "infirmier"]);

/** Le relecteur connecté, tel que identite le nomme. */
export type Relecteur = {
  sub: string;
  role: string;
  nom: string;
  etablissement: string;
  nom_etablissement: string;
};

/** Ce que rend un appel : le corps quand le statut est attendu, sinon le statut et le `detail` du refus (0 : injoignable). */
export type Reponse<T> = { ok: true; corps: T } | { ok: false; statut: number; detail?: unknown };

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
    const texte = await reponse.text();
    if (!attendus.includes(reponse.status)) {
      let detail: unknown;
      try {
        detail = texte ? (JSON.parse(texte) as { detail?: unknown }).detail : undefined;
      } catch {
        detail = undefined;
      }
      return { ok: false, statut: reponse.status, detail };
    }
    return { ok: true, corps: (texte ? JSON.parse(texte) : null) as T };
  } catch {
    // Seulement le fait : le journal ne cite ni la tâche ni ce qu'elle contient.
    console.warn("relecture : service injoignable");
    return { ok: false, statut: 0 };
  }
}

function enJson(methode: string, corps: unknown, entetes: Record<string, string> = {}): RequestInit {
  return { method: methode, headers: { "Content-Type": "application/json", ...entetes }, body: JSON.stringify(corps) };
}

/** Le relecteur connecté, ou `null` sans session valide (ou pour un rôle qui ne relit pas). */
export async function lireRelecteur(): Promise<Relecteur | null> {
  const reponse = await appeler<Relecteur>("/api/identite/session", [200]);
  return reponse.ok && ROLES_ADMIS.has(reponse.corps.role) ? reponse.corps : null;
}

/** L'agent de relecture relit et contrôle ; le médecin et l'infirmier valident. */
export function estSoignant(relecteur: Relecteur): boolean {
  return relecteur.role === "médecin" || relecteur.role === "infirmier";
}

/** Les étapes que ce rôle fait. */
export function etapesDe(relecteur: Relecteur): Etape[] {
  return estSoignant(relecteur) ? ["validation"] : ["relecture", "controle"];
}

function adresseDeLaTache(tache: string): string {
  return `/api/relecture/taches/${encodeURIComponent(tache)}`;
}

/** Les tâches de la semaine en cours du relecteur connecté, complétées jusqu'à son quota. */
export function lireMaSemaine(): Promise<Reponse<Tache[]>> {
  return appeler<Tache[]>("/api/relecture/taches", [200]);
}

/** Le suivi de l'agent de relecture : les comptes de la semaine et l'historique. */
export type Suivi = {
  semaine: { a_relire: number; confirmees: number; renvoyees: number; controlees: number };
  historique: { id: string; etape: Etape; date: string; issue: string | null }[];
};

export function lireSuivi(): Promise<Reponse<Suivi>> {
  return appeler<Suivi>("/api/relecture/suivi", [200]);
}

export function lireTache(tache: string): Promise<Reponse<TacheDetaillee>> {
  return appeler<TacheDetaillee>(adresseDeLaTache(tache), [200]);
}

/** Le brouillon du relecteur, si la tâche est encore à la version qu'il a lue ; rend la nouvelle version. */
export function enregistrer(tache: string, markdown: string, version: string): Promise<Reponse<{ id: string; version: string }>> {
  return appeler(`${adresseDeLaTache(tache)}/transcription`, [200], enJson("PUT", { markdown }, { "If-Match": `W/"${version}"` }));
}

export type Confirmation = { id: string; statut: string; transcription: string | null; relue: boolean; controle: string | null };

export function confirmer(tache: string, voletsVerifies: number[], resume: string): Promise<Reponse<Confirmation>> {
  return appeler(`${adresseDeLaTache(tache)}/confirmation`, [200, 201], enJson("POST", { volets_verifies: voletsVerifies, resume }));
}

export function controler(tache: string, decision: "accepter" | "renvoyer", note?: string): Promise<Reponse<unknown>> {
  return appeler(`${adresseDeLaTache(tache)}/controle`, [200, 201], enJson("POST", note ? { decision, note } : { decision }));
}

export function declarerInutilisable(tache: string, raison: "non-medical" | "doublon"): Promise<Reponse<unknown>> {
  return appeler(`${adresseDeLaTache(tache)}/inutilisable`, [200, 201], enJson("POST", { raison }));
}

export type Decision = { id: string; decision: "accepter" | "corriger" | "rejeter"; valeur?: string };

export function valider(tache: string, propositions: Decision[]): Promise<Reponse<unknown>> {
  return appeler(`${adresseDeLaTache(tache)}/validation`, [200, 201, 204], enJson("POST", { propositions }));
}

/** Une tâche reste à faire tant qu'elle n'est pas terminée. */
export function estFaite(tache: Pick<Tache, "statut">): boolean {
  return tache.statut === "terminee";
}

/** La prochaine tâche à faire de la semaine, autre que celle qu'on quitte ; `null` quand tout est fait. */
export async function tacheSuivante(sauf?: string): Promise<string | null> {
  const semaine = await lireMaSemaine();
  if (!semaine.ok) return null;
  return semaine.corps.find((tache) => !estFaite(tache) && tache.id !== sauf)?.id ?? null;
}
