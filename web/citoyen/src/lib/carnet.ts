// Le carnet, lu au service citoyen par la passerelle, avec le cookie de session du citoyen.
// L'application ne lit jamais le jeton, ne voit jamais le NPI, et ne garde rien de ce qu'elle reçoit.

import { cookies } from "next/headers";

const COOKIE_DE_SESSION = "__Host-session";
const DELAI_MS = 5000;

export type Moment = "matin" | "midi" | "soir" | "nuit";
export const MOMENTS: Moment[] = ["matin", "midi", "soir", "nuit"];
export const LIBELLES_DES_MOMENTS: Record<Moment, string> = { matin: "Matin", midi: "Midi", soir: "Soir", nuit: "Nuit" };

export type StatutDeLigne = "apayer" | "paye" | "aretirer" | "partiel" | "retire";

export type ResumeDeCas = {
  id: string;
  motif: string;
  en_cours: boolean;
  debut: string;
  fin: string | null;
  etablissement: string | null;
  visites: number;
};

export type MesureLue = { libelle: string; valeur: string; alerte: boolean };

export type VisiteLue = {
  id: string;
  date: string;
  type: string;
  urgence: boolean;
  etablissement: string | null;
  soignant: string | null;
  motif: string | null;
  mesures: MesureLue[];
  diagnostics: string[];
  ordonnance: string | null;
};

export type DetailDeCas = ResumeDeCas & { visites_lues: VisiteLue[] };

export type LigneLue = {
  id: string;
  produit: string;
  statut: StatutDeLigne;
  moments: Moment[];
  par_prise: number | null;
  jours: number | null;
  quantite: number | null;
  remis: number;
  unite: string;
  /** Payée, jamais remise : le pharmacien l'a arrêtée à cause d'une allergie déclarée. */
  arret_allergie: boolean;
};

export type OrdonnanceLue = {
  numero: string;
  date: string;
  etablissement: string | null;
  prescripteur: string | null;
  statut: StatutDeLigne;
  message: string;
  lignes: LigneLue[];
};

export type Prise = { produit: string; par_prise: number | null; unite: string | null; jour: number; jours: number };

export type TraitementDuJour = { date: string; moments: Record<Moment, Prise[]>; prochain: Moment | null };

export type AccesLu = {
  date: string;
  vous: boolean;
  qui: string;
  role: string | null;
  etablissement: string | null;
  service: string | null;
  motif: string;
  urgence: boolean;
  raison: string | null;
  /** Un dépôt : des papiers du citoyen ont été numérisés et ajoutés à son dossier. */
  depot?: boolean;
};

/** D'où vient une information (ADR 0007) : visite, declaration, report, numerisation ; null avant F5. */
export type Origine = string | null;

/** Un de mes documents : un papier numérisé, que personne n'a vérifié (`commun.fhir.documents.DocumentVu`). */
export type DocumentLu = {
  id: string;
  type: string;
  libelle: string;
  annee: string | null;
  etablissement: string | null;
  lisibilite: "lisible" | "partiel" | null;
  pages: number;
  /** Le format de chaque page : image/jpeg, image/png ou application/pdf. */
  formats: string[];
  origine: Origine;
  depose_le: string | null;
};

export type Accueil = {
  prenom: string;
  nom: string;
  cas_en_cours: number;
  cas_recent: ResumeDeCas | null;
  ordonnance: OrdonnanceLue | null;
  prochain_moment: Moment | null;
  prises_au_prochain_moment: number;
  dernier_acces: AccesLu | null;
  allergies: string[];
};

export type AllergieLue = { libelle: string; origine: Origine };
export type AntecedentLu = {
  type: "medical" | "chirurgical";
  libelle: string;
  depuis: string | null;
  actif: boolean;
  origine: Origine;
};
export type AntecedentFamilialLu = { lien: string; libelle: string; origine: Origine };
export type TraitementLu = { libelle: string; posologie: string | null; moments: Moment[]; depuis: string | null; origine: Origine };

export type MaSante = {
  groupe_sanguin: string | null;
  origine_du_groupe_sanguin: Origine;
  allergies: AllergieLue[];
  antecedents: AntecedentLu[];
  familiaux: AntecedentFamilialLu[];
  traitements: TraitementLu[];
};

/** Ce que le service a répondu : le carnet, ou pourquoi il n'est pas là. */
export type Lecture<T> =
  | { etat: "lu"; valeur: T }
  | { etat: "sans-session" }
  | { etat: "introuvable" }
  | { etat: "injoignable" };

function adressePasserelle(): string {
  const adresse = process.env.PASSERELLE_URL;
  if (!adresse) throw new Error("PASSERELLE_URL manquante : adresse interne de la passerelle pour cette application.");
  return adresse;
}

/** Lit `chemin` du service citoyen (`/carnet`, `/cas/…`) au nom du citoyen connecté. */
export async function lire<T>(chemin: string): Promise<Lecture<T>> {
  const jeton = (await cookies()).get(COOKIE_DE_SESSION)?.value;
  if (!jeton) return { etat: "sans-session" };
  try {
    const reponse = await fetch(`${adressePasserelle()}/api/citoyen${chemin}`, {
      cache: "no-store",
      headers: { Cookie: `${COOKIE_DE_SESSION}=${jeton}` },
      signal: AbortSignal.timeout(DELAI_MS),
    });
    if (reponse.status === 401 || reponse.status === 403) return { etat: "sans-session" };
    if (reponse.status === 404) return { etat: "introuvable" };
    if (!reponse.ok) {
      console.warn(`service citoyen : ${chemin} a répondu ${reponse.status}`);
      return { etat: "injoignable" };
    }
    return { etat: "lu", valeur: (await reponse.json()) as T };
  } catch (erreur) {
    console.warn(`service citoyen injoignable : ${chemin}`, erreur);
    return { etat: "injoignable" };
  }
}

const FUSEAU = "Africa/Porto-Novo";

function jourDe(date: Date): string {
  return new Intl.DateTimeFormat("fr-CA", { timeZone: FUSEAU }).format(date);
}

/** Une date en mots du quotidien : « aujourd'hui, 10:42 », « hier, 19:48 », « 12 septembre 2026 ». */
export function quand(iso: string, avecHeure = true): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  const heure = new Intl.DateTimeFormat("fr-FR", { timeZone: FUSEAU, hour: "2-digit", minute: "2-digit" }).format(date);
  const maintenant = new Date();
  const hier = new Date(maintenant.getTime() - 86_400_000);
  let jour: string;
  if (jourDe(date) === jourDe(maintenant)) jour = "Aujourd'hui";
  else if (jourDe(date) === jourDe(hier)) jour = "Hier";
  else jour = new Intl.DateTimeFormat("fr-FR", { timeZone: FUSEAU, day: "numeric", month: "long", year: "numeric" }).format(date);
  return avecHeure ? `${jour}, ${heure}` : jour;
}

/** Un nombre de comprimés en mots : « 1 comprimé », « 2 gélules », « ½ comprimé ». */
export function doses(nombre: number | null, unite: string | null): string {
  const n = nombre ?? 1;
  const mot = unite ?? "comprimé";
  if (n === 0.5) return `½ ${mot}`;
  return `${String(n).replace(".", ",")} ${mot}${n > 1 && !mot.endsWith("s") ? "s" : ""}`;
}

/** Le nom courant d'un produit : « Paracétamol » pour « Paracétamol 500 mg, comprimé ». */
export function nomCourt(produit: string): string {
  return produit.split(/[ ,]/)[0] ?? produit;
}
