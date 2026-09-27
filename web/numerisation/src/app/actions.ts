"use server";

import { LONGUEUR_NPI } from "@lafia/design";
import { redirect } from "next/navigation";

import { PIECES } from "../libelles";
import { clore, lireDepot, ouvrirDepot } from "../numerisation";

/** Pourquoi le dépôt ne s'est pas ouvert ; le NPI tapé reste dans le formulaire, jamais dans l'adresse. */
export type Refus = { erreur: "npi" | "piece" | "inconnu" | "service" } | null;

/** Ouvre le dépôt de la personne accueillie, puis montre qui c'est, à comparer avec sa pièce. */
export async function ouvrirLeDepot(_precedent: Refus, formulaire: FormData): Promise<Refus> {
  const npi = String(formulaire.get("npi") ?? "").replace(/\D/g, "");
  const piece = String(formulaire.get("piece") ?? "");
  const reprise = formulaire.get("reprise") === "oui";
  if (npi.length !== LONGUEUR_NPI) return { erreur: "npi" };
  if (!PIECES.some((p) => p.code === piece)) return { erreur: "piece" };

  const reponse = await ouvrirDepot(npi, piece, reprise);
  if (reponse.ok) redirect(`/depots/${encodeURIComponent(reponse.corps.depot_id)}/identite`);
  if (reponse.statut === 401 || reponse.statut === 403) redirect("/connexion");
  if (reponse.statut === 404) return { erreur: "inconnu" };
  if (reponse.statut === 422) return { erreur: "npi" };
  return { erreur: "service" };
}

/**
 * « Ce n'est pas la bonne personne » : le dépôt se ferme vide, ce qui n'écrit rien au dossier
 * (un dépôt sans Document n'a pas de Provenance), et l'accueil reprend.
 */
export async function abandonnerLeDepot(formulaire: FormData): Promise<void> {
  await clore(String(formulaire.get("depot") ?? ""));
  redirect("/?annule=1");
}

/** Clôt le dépôt ; l'écran suivant dit combien de Documents et de pages rendre avec les papiers. */
export async function cloreLeDepot(formulaire: FormData): Promise<void> {
  const depot = String(formulaire.get("depot") ?? "");
  // Le compte d'abord : une fois clos, le dépôt ne se lit plus.
  const lu = await lireDepot(depot);
  const reponse = await clore(depot);
  const chemin = `/depots/${encodeURIComponent(depot)}`;
  if (!reponse.ok) {
    if (reponse.statut === 401) redirect("/connexion");
    redirect(`${chemin}?erreur=${reponse.statut === 0 || reponse.statut >= 500 ? "service" : "clos"}`);
  }
  const documents = lu.ok ? lu.corps.documents : [];
  const pages = documents.reduce((total, document) => total + document.pages, 0);
  redirect(`${chemin}/clos?documents=${documents.length}&pages=${pages}`);
}
