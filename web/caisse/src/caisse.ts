// Le service caisse et identite, vus du serveur de l'application : joints par la passerelle, avec le
// jeton de session du caissier, que le navigateur a porté jusqu'ici dans son cookie.
import { cookies } from "next/headers";

const DELAI_MS = 5000;
/** Cookie du jeton, celui que les services lisent (`commun.jeton.COOKIE_DE_SESSION`). */
const COOKIE_DE_SESSION = "__Host-session";

/** Une ligne d'ordonnance, tarifée par l'établissement du caissier (`caisse.regles.encaissement.Ligne`). */
export type Ligne = {
  id: string;
  libelle: string;
  quantite: number;
  prix_unitaire: number;
  montant: number;
  payee: boolean;
};

export type Ordonnance = {
  numero: string;
  patient: { nom: string; prenoms: string };
  prescripteur: string;
  date: string;
  etablissement: string;
  lignes: Ligne[];
  total_a_payer: number;
};

export type Recepisse = {
  recepisse: string;
  numero: string;
  date: string;
  etablissement: string;
  montant: number;
  lignes: { id: string; libelle: string; montant: number }[];
};

/** Le caissier connecté, tel que identite le nomme. */
export type Caissier = {
  sub: string;
  role: string;
  nom: string;
  etablissement: string;
  nom_etablissement: string;
};

/** Ce que rend un appel : le corps quand le statut est attendu, sinon le statut seul (0 : injoignable). */
export type Reponse<T> = { ok: true; corps: T } | { ok: false; statut: number };

async function jeton(): Promise<string | undefined> {
  return (await cookies()).get(COOKIE_DE_SESSION)?.value;
}

async function appeler<T>(chemin: string, attendu: number, init: RequestInit = {}): Promise<Reponse<T>> {
  const passerelle = process.env.PASSERELLE_URL;
  const porte = await jeton();
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
    return { ok: true, corps: (await reponse.json()) as T };
  } catch {
    // Ni l'adresse ni le numéro : le journal ne cite rien qu'on ait tapé.
    console.warn("caisse : service injoignable");
    return { ok: false, statut: 0 };
  }
}

/** Le caissier connecté, ou `null` sans session valide (ou pour un autre rôle). */
export async function lireCaissier(): Promise<Caissier | null> {
  const reponse = await appeler<Caissier>("/api/identite/session", 200);
  return reponse.ok && reponse.corps.role === "caissier" ? reponse.corps : null;
}

export function lireOrdonnance(numero: string): Promise<Reponse<Ordonnance>> {
  return appeler<Ordonnance>(`/api/caisse/ordonnances/${encodeURIComponent(numero)}`, 200);
}

export function encaisser(numero: string, lignes: string[]): Promise<Reponse<Recepisse>> {
  return appeler<Recepisse>(`/api/caisse/ordonnances/${encodeURIComponent(numero)}/encaissements`, 201, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ lignes }),
  });
}

export function lireRecepisse(numero: string): Promise<Reponse<Recepisse>> {
  return appeler<Recepisse>(`/api/caisse/recepisses/${encodeURIComponent(numero)}`, 200);
}
