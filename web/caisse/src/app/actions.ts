"use server";

import { redirect } from "next/navigation";

import { encaisser } from "../caisse";

/** Ce que l'accueil dit d'un encaissement refusé (`/?numero=…&erreur=…`). */
const ERREURS: Record<number, string> = { 409: "deja-payee", 422: "aucune-ligne", 404: "introuvable" };

/** Encaisse les lignes cochées, puis ouvre le récépissé à imprimer. */
export async function encaisserLesLignes(formulaire: FormData): Promise<void> {
  const numero = String(formulaire.get("numero") ?? "");
  const lignes = formulaire.getAll("lignes").map(String);
  const reponse = lignes.length ? await encaisser(numero, lignes) : { ok: false as const, statut: 422 };
  if (reponse.ok) redirect(`/recepisses/${encodeURIComponent(reponse.corps.recepisse)}`);
  if (reponse.statut === 401 || reponse.statut === 403) redirect("/connexion");
  const erreur = ERREURS[reponse.statut] ?? "service";
  redirect(`/?numero=${encodeURIComponent(numero)}&erreur=${erreur}`);
}
