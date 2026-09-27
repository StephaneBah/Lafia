// Le service numerisation et identite, vus du serveur de l'application : joints par la passerelle, avec
// le jeton de session de l'agent, que le navigateur a porté jusqu'ici dans son cookie.
import { COOKIE_DE_SESSION } from "@lafia/commun";
import { cookies } from "next/headers";

const DELAI_MS = 5000;

/** Le rôle que les jetons portent pour un agent de numérisation (`commun.jeton.Role`). */
const ROLES_ADMIS = new Set(["agent de numérisation", "agent-numerisation"]);

/** L'agent connecté, tel que identite le nomme. */
export type Agent = {
  sub: string;
  role: string;
  nom: string;
  etablissement: string;
  nom_etablissement: string;
};

/** Ce que l'agent compare avec la pièce présentée : jamais le NPI, qu'il vient de taper. */
export type Patient = { nom: string; prenoms: string; annee_de_naissance: number | string };

export type DocumentDuDepot = {
  id: string;
  type: string;
  annee: string | number;
  pages: number;
  /** La note de l'agent quand le papier, abîmé en lui-même, a passé outre le contrôle de la capture. */
  papier_abime?: string | null;
};

export type Depot = { patient: Patient; documents: DocumentDuDepot[] };

export type DepotOuvert = { depot_id: string; patient: Patient };

/** Ce que rend un appel : le corps quand le statut est attendu, sinon le statut seul (0 : injoignable). */
export type Reponse<T> = { ok: true; corps: T } | { ok: false; statut: number };

async function appeler<T>(chemin: string, attendu: number, init: RequestInit = {}): Promise<Reponse<T>> {
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
    if (reponse.status !== attendu) return { ok: false, statut: reponse.status };
    const texte = await reponse.text();
    return { ok: true, corps: (texte ? JSON.parse(texte) : null) as T };
  } catch {
    // Ni l'adresse ni le NPI : le journal ne cite rien qu'on ait tapé.
    console.warn("numerisation : service injoignable");
    return { ok: false, statut: 0 };
  }
}

/** L'agent de numérisation connecté, ou `null` sans session valide (ou pour un autre rôle). */
export async function lireAgent(): Promise<Agent | null> {
  const reponse = await appeler<Agent>("/api/identite/session", 200);
  return reponse.ok && ROLES_ADMIS.has(reponse.corps.role) ? reponse.corps : null;
}

/** Ouvre le dépôt d'une personne : le NPI voyage dans le corps, jamais dans une adresse. */
export function ouvrirDepot(npi: string, piece: string, reprise: boolean): Promise<Reponse<DepotOuvert>> {
  return appeler<DepotOuvert>("/api/numerisation/depots", 201, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ npi, piece, reprise }),
  });
}

export function lireDepot(depot: string): Promise<Reponse<Depot>> {
  return appeler<Depot>(`/api/numerisation/depots/${encodeURIComponent(depot)}`, 200);
}

export function clore(depot: string): Promise<Reponse<unknown>> {
  return appeler<unknown>(`/api/numerisation/depots/${encodeURIComponent(depot)}/cloture`, 200, { method: "POST" });
}
