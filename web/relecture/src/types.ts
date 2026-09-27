// Ce que le service relecture rend, tel que les pages du serveur et les écrans du navigateur le lisent.
// Aucune identité de patient : ni NPI, ni nom, ni lieu du dépôt.

export type Etape = "relecture" | "controle" | "validation";
export type Statut = "a-faire" | "en-cours" | "terminee";

/** Ce que le relecteur voit du Document : ce que l'agent de numérisation a déclaré, jamais à qui il est. */
export type DocumentARelire = {
  type: string;
  libelle?: string;
  annee: string | number | null;
  pages: number;
  /** Le format de chaque page, dans l'ordre : image/jpeg, image/png ou application/pdf. */
  formats?: string[];
};

/** Une ligne de « Ma semaine ». */
export type Tache = {
  id: string;
  etape: Etape;
  statut: Statut;
  document: DocumentARelire;
  echeance: string | null;
  /** Une Relecture que le Contrôle a renvoyée, pas encore confirmée de nouveau. */
  renvoyee: boolean;
};

/** Un fait que la machine propose, à accepter, corriger ou rejeter par un soignant. */
export type Proposition = {
  id: string;
  type: string;
  libelle: string;
  valeur: string | null;
  confiance: number | null;
  extrait?: string | null;
};

export type Modele = { nom: string; version: string; demonstration: boolean };

export type NoteDeControle = { date: string | null; texte: string };

export type TacheDetaillee = Tache & {
  /** À renvoyer en If-Match avec chaque brouillon. */
  version: string;
  markdown: string | null;
  volets: { rang: number; titre: string; type: string; date: string | null; etablissement: string | null; pages: number[] }[];
  erreurs: string[];
  texte: string | null;
  modele: Modele | null;
  notes_de_controle: NoteDeControle[];
  resume: string | null;
  propositions?: Proposition[] | null;
};
