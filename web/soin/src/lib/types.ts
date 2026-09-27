// Ce que le service soin rend, tel que les pages et les composants le lisent.

export type Moment = "matin" | "midi" | "soir" | "nuit";
export const MOMENTS: Moment[] = ["matin", "midi", "soir", "nuit"];

/** Un produit ou un acte du catalogue ; `forme` : l'unité d'une quantité (comprimé, flacon…). */
export type Produit = { code: string; libelle: string; prix: number; atc: string | null; forme?: string | null };
export type MesureDuCatalogue = { code: string; libelle: string; unite: string };
export type DiagnosticDuCatalogue = { code: string; libelle: string };
export type AllergieDuCatalogue = { code_atc: string; libelle: string };
export type Catalogue = {
  produits: Produit[];
  mesures: MesureDuCatalogue[];
  diagnostics: DiagnosticDuCatalogue[];
  allergies?: AllergieDuCatalogue[];
};

export type Patient = {
  id: string;
  npi?: string;
  nom: string;
  prenoms: string;
  sexe: string;
  naissance: string | null;
  age?: number | null;
};
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
export type TypeDAntecedent = "medical" | "chirurgical";
export type Antecedent = { id: string; type: TypeDAntecedent; libelle: string; depuis: string | null; actif: boolean };
export type AntecedentFamilial = { id: string; lien: string; libelle: string };
export type Traitement = { id: string; libelle: string; posologie: string; moments: Moment[]; depuis: string | null };

/**
 * Le bandeau patient (`GET /api/soin/patients/{id}`). Sans relation de soin, le service omet
 * antécédents, familiaux et traitements : identité, allergies et groupe sanguin restent, ils sauvent.
 */
export type Bandeau = {
  patient: Patient;
  groupe_sanguin: string | null;
  allergies: Allergie[];
  antecedents?: Antecedent[];
  familiaux?: AntecedentFamilial[];
  traitements?: Traitement[];
  cas: TitreDeCas[];
  relation_de_soin: boolean;
};

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
export type PointDeMesure = { date: string; valeur: number | string };
export type Dossier = {
  patient: Patient;
  allergies: Allergie[];
  cas: Cas[];
  /** Les séries de mesures par code LOINC, dans l'ordre des dates, pour les courbes. */
  mesures_series?: Record<string, PointDeMesure[]>;
};

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
  lignes: { produit: string; dose: number; moments: Moment[]; jours: number; quantite: number; unite?: string | null }[];
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

/** Le NPI masqué à l'écran : les six derniers chiffres seulement, assez pour le vérifier avec le patient. */
export function npiMasque(npi: string | undefined): string {
  if (!npi) return "";
  const fin = npi.slice(-6);
  return `••• ${fin.slice(0, 3)} ${fin.slice(3)}`;
}

/** Les groupes sanguins qu'on enregistre. */
export const GROUPES_SANGUINS = ["A+", "A−", "B+", "B−", "AB+", "AB−", "O+", "O−"] as const;

/** Le lien de parenté d'un antécédent familial, tel que le service l'attend, avec son libellé. */
export const LIENS_DE_PARENTE = [
  ["mere", "Mère"],
  ["pere", "Père"],
  ["fratrie", "Frère ou sœur"],
  ["enfant", "Enfant"],
  ["grand-parent", "Grand-parent"],
] as const;

/** Le libellé d'un lien de parenté rendu par le service (code ou texte). */
export function libelleDuLien(lien: string): string {
  return LIENS_DE_PARENTE.find(([code]) => code === lien)?.[1] ?? lien;
}

export const LIBELLES_DES_MOMENTS: Record<Moment, string> = { matin: "Matin", midi: "Midi", soir: "Soir", nuit: "Nuit" };

/** Initiales du patient pour son avatar. */
export function initiales(patient: Patient): string {
  return `${patient.prenoms.charAt(0)}${patient.nom.charAt(0)}`.toUpperCase();
}

/** Une allergie qui touche ce produit : sa classe ATC préfixe celle du produit. */
export function allergieDuProduit(produit: Produit | undefined, allergies: Allergie[]): Allergie | undefined {
  if (!produit?.atc) return undefined;
  return allergies.find((a) => a.code_atc && produit.atc!.startsWith(a.code_atc));
}
