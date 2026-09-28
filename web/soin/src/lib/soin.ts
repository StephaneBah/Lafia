import { cookies, headers } from "next/headers";

import type { Bandeau, Catalogue, DocumentDuDossier, Dossier, Moment, SessionSoignant, TranscriptionDuDocument } from "./types";

// Le service soin et identite, joints par la passerelle depuis le serveur de l'application, avec le
// jeton de session du soignant : l'application ne lit jamais le jeton, elle le transmet.

const COOKIE_DE_SESSION = "__Host-session";
const DELAI_MS = 8000;

function passerelle(): string {
  const adresse = process.env.PASSERELLE_URL;
  if (!adresse) throw new Error("PASSERELLE_URL manquante : adresse interne de la passerelle pour cette application.");
  return adresse;
}

export type Reponse<T> = { statut: number; corps: T | null };

async function appeler<T>(methode: "GET" | "POST" | "PUT", chemin: string, corps?: unknown): Promise<Reponse<T>> {
  const jeton = (await cookies()).get(COOKIE_DE_SESSION)?.value;
  if (!jeton) return { statut: 401, corps: null };
  const enTetes: Record<string, string> = { Cookie: `${COOKIE_DE_SESSION}=${jeton}` };
  if (corps !== undefined) enTetes["Content-Type"] = "application/json";
  try {
    const reponse = await fetch(`${passerelle()}${chemin}`, {
      method: methode,
      cache: "no-store",
      headers: enTetes,
      body: corps === undefined ? undefined : JSON.stringify(corps),
      signal: AbortSignal.timeout(DELAI_MS),
    });
    const texte = await reponse.text();
    let lu: T | null = null;
    try {
      lu = texte ? (JSON.parse(texte) as T) : null;
    } catch {
      lu = null;
    }
    if (!reponse.ok) console.warn(`${methode} ${chemin.replace(/\d{13}/, "<npi>")} : ${reponse.status}`);
    return { statut: reponse.status, corps: lu };
  } catch (erreur) {
    console.warn(`passerelle injoignable : ${chemin.split("/").slice(0, 4).join("/")}`, erreur);
    return { statut: 503, corps: null };
  }
}

const patient = (id: string) => `/api/soin/patients/${encodeURIComponent(id)}`;

// Le patient est désigné par son id de ressource Patient : le NPI ne part qu'une fois, dans le corps
// de la recherche, et n'entre jamais dans une adresse ni un journal.
export const soin = {
  catalogue: () => appeler<Catalogue>("GET", "/api/soin/catalogue"),
  rechercher: (npi: string) => appeler<{ patient_id: string }>("POST", "/api/soin/recherche", { npi }),
  bandeau: (id: string) => appeler<Bandeau>("GET", patient(id)),
  dossier: (id: string) => appeler<Dossier>("GET", `${patient(id)}/dossier`),
  ouvrirCas: (id: string, motif: string) => appeler<{ cas_id: string }>("POST", `${patient(id)}/cas`, { motif }),
  enregistrerVisite: (casId: string, visite: unknown) =>
    appeler<{ visite_id: string; numero_ordonnance: string | null; detail?: unknown }>("POST", `/api/soin/cas/${encodeURIComponent(casId)}/visites`, visite),
  clore: (casId: string) => appeler<unknown>("POST", `/api/soin/cas/${encodeURIComponent(casId)}/cloture`),
  urgence: (id: string, raison: string) => appeler<{ cas_id: string; visite_id: string }>("POST", `${patient(id)}/acces-urgence`, { raison }),
  allergie: (id: string, code_atc: string, libelle: string, document_id?: string) =>
    appeler<unknown>("POST", `${patient(id)}/allergies`, { code_atc, libelle, ...(document_id && { document_id }) }),
  antecedent: (
    id: string,
    antecedent: {
      type: "medical" | "chirurgical" | "familial";
      libelle: string;
      depuis?: string;
      lien?: string;
      actif?: boolean;
      document_id?: string;
    },
  ) => appeler<{ id: string }>("POST", `${patient(id)}/antecedents`, antecedent),
  traitement: (id: string, traitement: { produit?: string; libelle?: string; posologie: string; moments: Moment[] }) =>
    appeler<{ id: string }>("POST", `${patient(id)}/traitements`, traitement),
  arreterTraitement: (traitementId: string) => appeler<unknown>("POST", `/api/soin/traitements/${encodeURIComponent(traitementId)}/arret`),
  groupeSanguin: (id: string, valeur: string) => appeler<unknown>("PUT", `${patient(id)}/groupe-sanguin`, { valeur }),
  documents: (id: string) => appeler<DocumentDuDossier[]>("GET", `${patient(id)}/documents`),
  transcription: (documentId: string) =>
    appeler<TranscriptionDuDocument>("GET", `/api/soin/documents/${encodeURIComponent(documentId)}/transcription`),
};

/** Le soignant connecté, qu'identite lit du jeton ; `null` sans session valide. */
export async function lireSession(): Promise<SessionSoignant | null> {
  const reponse = await appeler<SessionSoignant>("GET", "/api/identite/session");
  if (reponse.statut !== 200 || !reponse.corps) return null;
  return reponse.corps.role === "médecin" || reponse.corps.role === "infirmier" ? reponse.corps : null;
}

/** Un nouveau code carnet pour le reçu, émis par identite pour ce NPI (ADR 0005) ; `null` si refusé. */
export async function emettreCodeCarnet(npi: string): Promise<string | null> {
  const reponse = await appeler<{ code: string }>("POST", "/api/identite/codes-carnet", { npi });
  return reponse.statut === 201 && reponse.corps ? reponse.corps.code : null;
}

/** L'hôte du domaine, sans le sous-domaine de l'application : `citoyen.<domaine>`, le site. */
export async function domaine(): Promise<string> {
  const hote = ((await headers()).get("host") ?? "").replace(/:\d+$/, "");
  return hote.split(".").slice(1).join(".") || "localhost";
}
