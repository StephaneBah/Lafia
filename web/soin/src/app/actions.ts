"use server";

import { redirect } from "next/navigation";

import { emettreCodeCarnet, lireSession, soin } from "../lib/soin";
import { MOMENTS, type Moment, type Recu } from "../lib/types";

// Les formulaires de l'application : chacun appelle le service soin par la passerelle, avec la session
// du soignant, puis mène à l'écran suivant.

const NPI = /^\d{13}$/;

function texte(donnees: FormData, nom: string): string {
  const valeur = donnees.get(nom);
  return typeof valeur === "string" ? valeur.trim() : "";
}

function nombre(donnees: FormData, nom: string): number | null {
  const brut = texte(donnees, nom).replace(",", ".");
  if (!brut) return null;
  const n = Number(brut);
  return Number.isFinite(n) ? n : null;
}

function npiValide(donnees: FormData): string {
  const npi = texte(donnees, "npi").replace(/\D/g, "");
  if (!NPI.test(npi)) redirect("/?erreur=npi");
  return npi;
}

export async function rechercher(donnees: FormData) {
  redirect(`/patients/${npiValide(donnees)}`);
}

export async function ouvrirCas(donnees: FormData) {
  const npi = npiValide(donnees);
  const motif = texte(donnees, "motif");
  if (!motif) redirect(`/patients/${npi}?erreur=motif`);
  const reponse = await soin.ouvrirCas(npi, motif);
  if (reponse.statut !== 201 || !reponse.corps) redirect(`/patients/${npi}?erreur=service`);
  redirect(`/patients/${npi}/visite?cas=${reponse.corps.cas_id}`);
}

export async function cloreCas(donnees: FormData) {
  const npi = npiValide(donnees);
  const cas = texte(donnees, "cas");
  const reponse = await soin.clore(cas);
  redirect(`/patients/${npi}/dossier${reponse.statut === 200 ? "?clos=1" : "?erreur=cloture"}`);
}

export async function accesDUrgence(donnees: FormData) {
  const npi = npiValide(donnees);
  const motif = texte(donnees, "motif");
  const precision = texte(donnees, "precision");
  const raison = [motif, precision].filter(Boolean).join(" : ");
  if (raison.length < 10) redirect(`/patients/${npi}/urgence?erreur=raison`);
  const reponse = await soin.urgence(npi, raison);
  if (reponse.statut !== 201) redirect(`/patients/${npi}/urgence?erreur=service`);
  redirect(`/patients/${npi}/dossier?urgence=1`);
}

export async function declarerAllergie(donnees: FormData) {
  const npi = npiValide(donnees);
  const [code, ...libelle] = texte(donnees, "allergie").split("|");
  const reponse = await soin.allergie(npi, code, libelle.join("|"));
  redirect(`/patients/${npi}/dossier${reponse.statut === 201 ? "" : "?erreur=allergie"}`);
}

export type EtatDeVisite = { erreur?: string; recu?: Recu } | null;

/**
 * Enregistre la visite, puis demande à identite le code carnet du reçu. Le reçu revient à l'écran,
 * jamais dans une adresse : le code carnet ne figure dans aucun journal.
 */
export async function enregistrerVisite(_: EtatDeVisite, donnees: FormData): Promise<EtatDeVisite> {
  const npi = npiValide(donnees);
  const cas = texte(donnees, "cas");
  const type = texte(donnees, "type") || "consultation";
  const motif = texte(donnees, "motif");
  if (!motif) return { erreur: "Le motif de la visite est obligatoire." };

  const mesures: { code: string; valeur: number | string; valeur2?: number }[] = [];
  for (const code of ["8310-5", "8867-4", "29463-7", "59408-5", "2339-0", "718-7"]) {
    const valeur = nombre(donnees, `m-${code}`);
    if (valeur !== null) mesures.push({ code, valeur });
  }
  const systolique = nombre(donnees, "m-85354-9");
  const diastolique = nombre(donnees, "m-85354-9-2");
  if (systolique !== null && diastolique !== null) mesures.push({ code: "85354-9", valeur: systolique, valeur2: diastolique });
  const tdr = texte(donnees, "m-70569-9");
  if (tdr) mesures.push({ code: "70569-9", valeur: tdr });

  const codeDiagnostic = texte(donnees, "diagnostic");
  const diagnostic = codeDiagnostic
    ? { code: codeDiagnostic, confirme: donnees.get("confirme") === "on", note: texte(donnees, "note") || null }
    : null;

  const indices = texte(donnees, "lignes").split(",").filter(Boolean);
  const ordonnance = indices
    .map((i) => ({
      produit: texte(donnees, `l-${i}-produit`),
      quantite: nombre(donnees, `l-${i}-quantite`) ?? 1,
      dose: nombre(donnees, `l-${i}-dose`) ?? 1,
      moments: donnees.getAll(`l-${i}-moments`).filter((m): m is Moment => MOMENTS.includes(m as Moment)),
      jours: nombre(donnees, `l-${i}-jours`) ?? 1,
    }))
    .filter((l) => l.produit);

  const reponse = await soin.enregistrerVisite(cas, {
    type,
    motif,
    mesures,
    diagnostic,
    ordonnance: ordonnance.length ? ordonnance : null,
  });
  if (reponse.statut === 409) return { erreur: "Ce cas est clos : ouvrez-en un nouveau." };
  if (reponse.statut === 422) return { erreur: "Une valeur sort du catalogue : vérifiez les mesures et l'ordonnance." };
  if (reponse.statut !== 201 || !reponse.corps) return { erreur: "Le service soin n'a pas enregistré la visite. Réessayez." };

  const [code, session] = await Promise.all([emettreCodeCarnet(npi), lireSession()]);
  return {
    recu: {
      numero: reponse.corps.numero_ordonnance,
      code,
      date: new Date().toISOString(),
      etablissement: session?.nom_etablissement ?? "",
      soignant: session?.nom ?? "",
      patient: texte(donnees, "patient"),
      lignes: ordonnance,
    },
  };
}
