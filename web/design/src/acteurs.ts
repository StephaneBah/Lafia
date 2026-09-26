// Les acteurs de Lafia et leur adresse : une application par acteur, chacune sur son sous-domaine,
// et le site produit sur le domaine lui-même.

import type { NomIcone } from "./generes/icones";

export type Acteur = "citoyen" | "soin" | "caisse" | "pharmacie";

export const ACTEURS: Record<Acteur, { libelle: string; icone: NomIcone }> = {
  citoyen: { libelle: "Carnet citoyen", icone: "user" },
  soin: { libelle: "Soin", icone: "stethoscope" },
  caisse: { libelle: "Caisse", icone: "cash-register" },
  pharmacie: { libelle: "Pharmacie", icone: "pill" },
};

/** L'ordre dans lequel le site et son pied de page présentent les applications. */
export const ORDRE_DES_ACTEURS: Acteur[] = ["citoyen", "soin", "caisse", "pharmacie"];

/** Le nom d'hôte d'une application : `soin.lafia.stephanebah.page`. */
export function hoteDApplication(acteur: Acteur, domaine: string): string {
  return `${acteur}.${domaine}`;
}

/** L'adresse d'une application, ou du site quand aucun acteur n'est donné. */
export function adresse(domaine: string, acteur?: Acteur): string {
  return `https://${acteur ? hoteDApplication(acteur, domaine) : domaine}`;
}
