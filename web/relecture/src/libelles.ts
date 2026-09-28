// Ce que la relecture nomme, avec les codes que le service attend (docs/specs/F6-relecture-et-extraction.md).
// Partagé par les pages du serveur et les écrans du navigateur : rien ici ne lit la session.
import type { Acteur, NomIcone } from "@lafia/design";

import type { DocumentARelire, Etape, Tache } from "./types";

export const ACTEUR: Acteur = "relecture";

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

/** Le mot du type de Document : celui que le service donne, sinon celui de la liste. */
export function libelleDuDocument(document: Pick<DocumentARelire, "type" | "libelle">): string {
  return document.libelle || TYPES_DE_DOCUMENT.find((type) => type.code === document.type)?.libelle || document.type;
}

export function iconeDuType(code: string): NomIcone {
  return TYPES_DE_DOCUMENT.find((type) => type.code === code)?.icone ?? "list";
}

/** Le Document en une ligne : type, année, pages. */
export function descriptionDuDocument(document: DocumentARelire): string {
  return [libelleDuDocument(document), document.annee ?? "année inconnue", pluriel(document.pages, "page")].join(" · ");
}

export const LIBELLES_DES_ETAPES: Record<Etape, string> = {
  relecture: "Relecture",
  controle: "Contrôle",
  validation: "Validation",
};

/** L'état d'une tâche, en mots, avec son icône et son ton : jamais la couleur seule. */
export function etatDeLaTache(tache: Pick<Tache, "etape" | "statut" | "renvoyee">): {
  libelle: string;
  icone: NomIcone;
  ton: "a-faire" | "renvoyee" | "faite";
} {
  const faite = tache.statut === "terminee";
  if (tache.etape === "relecture") {
    if (faite) return { libelle: "Confirmée", icone: "check", ton: "faite" };
    if (tache.renvoyee) return { libelle: "Renvoyée", icone: "arrow-left", ton: "renvoyee" };
    return { libelle: tache.statut === "en-cours" ? "À relire · commencée" : "À relire", icone: "clock", ton: "a-faire" };
  }
  if (tache.etape === "controle") {
    return faite ? { libelle: "Contrôlée", icone: "check", ton: "faite" } : { libelle: "À contrôler", icone: "eye", ton: "a-faire" };
  }
  return faite ? { libelle: "Validée", icone: "check", ton: "faite" } : { libelle: "À valider", icone: "stethoscope", ton: "a-faire" };
}

/** L'issue d'une tâche de l'historique, en mots. */
export function libelleDeLIssue(issue: string | null): string {
  const libelles: Record<string, string> = {
    confirmee: "Confirmée, contrôle en attente",
    relue: "Relue",
    renvoyee: "Renvoyée au relecteur",
    acceptee: "Acceptée",
    "non-medical": "Close : pas un document médical",
    doublon: "Close : déjà numérisé",
  };
  return (issue && libelles[issue]) || "Terminée";
}

/** Les raisons de clore une Relecture sans Transcription. */
export const RAISONS_D_INUTILISABLE: { code: "non-medical" | "doublon"; libelle: string; aide: string; icone: NomIcone }[] = [
  { code: "non-medical", libelle: "Pas un document médical", aide: "Facture, courrier, page blanche…", icone: "x" },
  { code: "doublon", libelle: "Déjà numérisé", aide: "Les mêmes pages existent déjà dans un autre Document.", icone: "copy" },
];

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

/** L'adresse d'une page de la tâche, vue du navigateur : même origine, par la passerelle, avec le cookie. */
export function adresseDeLaPage(tache: string, page: number): string {
  return `/api/relecture/taches/${encodeURIComponent(tache)}/pages/${page}`;
}

export function pluriel(nombre: number, singulier: string, plurielle = `${singulier}s`): string {
  return `${nombre} ${nombre > 1 ? plurielle : singulier}`;
}
