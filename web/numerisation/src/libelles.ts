// Ce que le bureau nomme, avec les codes que le service attend (docs/specs/F5-reprise-du-passe-medical.md).
// Partagé par les pages du serveur et le formulaire du navigateur : rien ici ne lit la session.
import type { Acteur, NomIcone } from "@lafia/design";

/**
 * L'acteur de l'application, pour l'en-tête, la connexion et l'état du service. Le système de design
 * le déclare avec F5.2 ; la conversion tient jusque-là.
 */
export const ACTEUR = "numerisation" as Acteur;

export const TITRE = "Numérisation";

/** La pièce d'identité que l'agent a vue et vérifiée, déclarée au dépôt. */
export const PIECES: { code: string; libelle: string }[] = [
  { code: "cni", libelle: "Carte nationale d'identité" },
  { code: "passeport", libelle: "Passeport" },
  { code: "acte-de-naissance", libelle: "Acte de naissance" },
  { code: "carte-lafia", libelle: "Carte biométrique" },
  { code: "autre", libelle: "Autre" },
];

/** Les types de Document (`TYPE_DE_DOCUMENT`), chacun avec son icône et son mot. */
export const TYPES_DE_DOCUMENT: { code: string; libelle: string; icone: NomIcone }[] = [
  { code: "carnet", libelle: "Carnet de santé", icone: "heartbeat" },
  { code: "compte-rendu", libelle: "Compte rendu", icone: "stethoscope" },
  { code: "resultat-analyse", libelle: "Résultat d'analyse", icone: "test-tube" },
  { code: "ordonnance", libelle: "Ancienne ordonnance", icone: "pill" },
  { code: "imagerie", libelle: "Imagerie", icone: "eye" },
  { code: "certificat", libelle: "Certificat", icone: "shield-check" },
  { code: "autre", libelle: "Autre", icone: "list" },
];

export const LISIBILITES: { code: string; libelle: string; icone: NomIcone }[] = [
  { code: "lisible", libelle: "Lisible", icone: "check" },
  { code: "partiel", libelle: "Partiellement lisible", icone: "warning" },
];

export function libelleDuType(code: string): string {
  return TYPES_DE_DOCUMENT.find((type) => type.code === code)?.libelle ?? code;
}

export function iconeDuType(code: string): NomIcone {
  return TYPES_DE_DOCUMENT.find((type) => type.code === code)?.icone ?? "list";
}

/** L'adresse d'un dépôt, vue du navigateur : même origine, par la passerelle, avec le cookie de session. */
export function adresseDuDepot(depot: string): string {
  return `/api/numerisation/depots/${encodeURIComponent(depot)}`;
}

export function pluriel(nombre: number, singulier: string, plurielle = `${singulier}s`): string {
  return `${nombre} ${nombre > 1 ? plurielle : singulier}`;
}
