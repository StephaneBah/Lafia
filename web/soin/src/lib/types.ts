// Ce que le service soin rend, tel que les pages et les composants le lisent.

export type Moment = "matin" | "midi" | "soir" | "nuit";
export const MOMENTS: Moment[] = ["matin", "midi", "soir", "nuit"];

export type Produit = { code: string; libelle: string; prix: number; atc: string | null };
export type MesureDuCatalogue = { code: string; libelle: string; unite: string };
export type DiagnosticDuCatalogue = { code: string; libelle: string };
export type Catalogue = { produits: Produit[]; mesures: MesureDuCatalogue[]; diagnostics: DiagnosticDuCatalogue[] };

export type Patient = { id: string; nom: string; prenoms: string; sexe: string; naissance: string | null };
export type Allergie = { id: string; libelle: string; code_atc: string | null };
export type TitreDeCas = {
  id: string;
  motif: string;
  statut: "en-cours" | "termine";
  etablissement: string;
  etablissement_id: string | null;
  debut: string | null;
  de_mon_etablissement: boolean;
};
export type Fiche = { patient: Patient; allergies: Allergie[]; cas: TitreDeCas[]; relation_de_soin: boolean };

export type Mesure = { id: string; code: string; libelle: string; valeur: string; unite: string; date: string | null };
export type Diagnostic = { id: string; code: string; libelle: string; confirme: boolean; note: string | null };
export type Ligne = {
  id: string;
  produit: string | null;
  libelle: string;
  quantite: number | null;
  dose: number | null;
  moments: Moment[];
  jours: number | null;
  posologie: string;
};
export type Visite = {
  id: string;
  type: string;
  type_libelle: string;
  urgence: boolean;
  date: string | null;
  motif: string;
  etablissement: string;
  soignant: string;
  mesures: Mesure[];
  diagnostics: Diagnostic[];
  ordonnance: { numero: string | null; lignes: Ligne[] } | null;
};
export type Cas = {
  id: string;
  motif: string;
  statut: "en-cours" | "termine";
  etablissement: string;
  debut: string | null;
  fin: string | null;
  visites: Visite[];
};
export type Dossier = { patient: Patient; npi: string; allergies: Allergie[]; cas: Cas[] };

/** Un agent connecté, tel qu'identite le rend (`GET /api/identite/session`). */
export type SessionSoignant = {
  sub: string;
  role: "médecin" | "infirmier";
  etablissement: string;
  nom: string;
  nom_etablissement: string;
};

/** Ce que le reçu imprime, rendu par l'enregistrement d'une visite. */
export type Recu = {
  numero: string | null;
  code: string | null;
  date: string;
  etablissement: string;
  soignant: string;
  patient: string;
  lignes: { produit: string; dose: number; moments: Moment[]; jours: number; quantite: number }[];
};

/** L'âge en années, depuis une date de naissance ISO. */
export function age(naissance: string | null): number | null {
  if (!naissance) return null;
  const n = new Date(naissance);
  const auj = new Date();
  let a = auj.getFullYear() - n.getFullYear();
  if (auj.getMonth() < n.getMonth() || (auj.getMonth() === n.getMonth() && auj.getDate() < n.getDate())) a -= 1;
  return a;
}

/** Initiales du patient pour son avatar. */
export function initiales(patient: Patient): string {
  return `${patient.prenoms.charAt(0)}${patient.nom.charAt(0)}`.toUpperCase();
}

/** Une allergie qui touche ce produit : sa classe ATC préfixe celle du produit. */
export function allergieDuProduit(produit: Produit | undefined, allergies: Allergie[]): Allergie | undefined {
  if (!produit?.atc) return undefined;
  return allergies.find((a) => a.code_atc && produit.atc!.startsWith(a.code_atc));
}
