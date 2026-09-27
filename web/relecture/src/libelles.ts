// Ce que la relecture nomme, avec les codes que le service attend (docs/specs/F6-relecture-et-extraction.md).
// Partagé par les pages du serveur et les formulaires du navigateur : rien ici ne lit la session.
import type { Acteur, NomIcone } from "@lafia/design";

/**
 * L'acteur de l'application, pour l'en-tête, la connexion et l'état du service. Le système de design
 * le déclare avec F6.3 ; la conversion tient jusque-là.
 */
export const ACTEUR = "relecture" as Acteur;

export const TITRE = "Relecture";

/** Les types de Document (`TYPE_DE_DOCUMENT`), chacun avec son icône et son mot, comme au bureau de numérisation. */
export const TYPES_DE_DOCUMENT: { code: string; libelle: string; icone: NomIcone }[] = [
  { code: "carnet", libelle: "Carnet de santé", icone: "heartbeat" },
  { code: "compte-rendu", libelle: "Compte rendu", icone: "stethoscope" },
  { code: "resultat-analyse", libelle: "Résultat d'analyse", icone: "test-tube" },
  { code: "ordonnance", libelle: "Ancienne ordonnance", icone: "pill" },
  { code: "imagerie", libelle: "Imagerie", icone: "eye" },
  { code: "certificat", libelle: "Certificat", icone: "shield-check" },
  { code: "autre", libelle: "Autre", icone: "list" },
];

export function libelleDuType(code: string): string {
  return TYPES_DE_DOCUMENT.find((type) => type.code === code)?.libelle ?? code;
}

export function iconeDuType(code: string): NomIcone {
  return TYPES_DE_DOCUMENT.find((type) => type.code === code)?.icone ?? "list";
}

export function libelleDeLisibilite(code?: string): string | null {
  if (!code) return null;
  return { lisible: "Lisible", partiel: "Partiellement lisible" }[code] ?? code;
}

/** Les verdicts du triage : icône et mot, toujours ensemble. `mauvais-type` demande le bon type. */
export const VERDICTS: { code: string; libelle: string; aide: string; icone: NomIcone }[] = [
  { code: "utilisable", libelle: "Utilisable", aide: "Lisible, médical, du bon type : la machine peut le lire.", icone: "check" },
  { code: "illisible", libelle: "Illisible", aide: "Trop flou, trop sombre, coupé.", icone: "eye" },
  { code: "non-medical", libelle: "Pas un document médical", aide: "Facture, courrier, page blanche…", icone: "x" },
  { code: "mauvais-type", libelle: "Type à corriger", aide: "Médical, mais pas du type déclaré.", icone: "list" },
  { code: "doublon", libelle: "Déjà numérisé", aide: "La même page existe déjà dans une autre tâche.", icone: "copy" },
];

export function libelleDuVerdict(code?: string | null): string {
  return VERDICTS.find((verdict) => verdict.code === code)?.libelle ?? "Fait";
}

/** Les ressources que l'Extraction propose (ADR 0009), dites avec les mots du dossier. */
const TYPES_DE_PROPOSITION: Record<string, { libelle: string; icone: NomIcone }> = {
  Observation: { libelle: "Mesure", icone: "chart-line" },
  Condition: { libelle: "Antécédent", icone: "stethoscope" },
  AllergyIntolerance: { libelle: "Allergie", icone: "warning" },
  MedicationStatement: { libelle: "Traitement", icone: "pill" },
};

export function genreDeProposition(type: string): { libelle: string; icone: NomIcone } {
  return TYPES_DE_PROPOSITION[type] ?? { libelle: type, icone: "list" };
}

/** La confiance du modèle en mots, avec son nombre : une proportion (0,87) ou un pourcentage (87). */
export function confiance(valeur: number): { mot: string; pourcent: number; niveau: "elevee" | "moyenne" | "faible" } {
  const pourcent = Math.round(valeur <= 1 ? valeur * 100 : valeur);
  if (pourcent >= 80) return { mot: "confiance élevée", pourcent, niveau: "elevee" };
  if (pourcent >= 50) return { mot: "confiance moyenne", pourcent, niveau: "moyenne" };
  return { mot: "confiance faible", pourcent, niveau: "faible" };
}

/** Le modèle qui tient la place du vrai, tant qu'il n'existe pas (ADR 0009). */
export function estDeDemonstration(modele?: { nom: string } | null): boolean {
  return modele?.nom === "demonstration";
}

/** L'adresse d'une page de la tâche, vue du navigateur : même origine, par la passerelle, avec le cookie. */
export function adresseDeLaPage(tache: string, page: number): string {
  return `/api/relecture/taches/${encodeURIComponent(tache)}/pages/${page}`;
}

export function pluriel(nombre: number, singulier: string, plurielle = `${singulier}s`): string {
  return `${nombre} ${nombre > 1 ? plurielle : singulier}`;
}

/** L'année la plus ancienne qu'un Document peut porter, et la plus récente : celle en cours. */
export const ANNEE_MIN = 1900;
