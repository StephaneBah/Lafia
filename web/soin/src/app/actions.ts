"use server";

import { redirect } from "next/navigation";

import { emettreCodeCarnet, lireSession, soin } from "../lib/soin";
import { GROUPES_SANGUINS, LIENS_DE_PARENTE, MOMENTS, TYPES_DE_DOCUMENT, type Moment, type Recu } from "../lib/types";

// Les formulaires de l'application : chacun appelle le service soin par la passerelle, avec la session
// du soignant, puis mène à l'écran suivant. Le patient y est désigné par son id de ressource : le NPI
// n'entre que dans la recherche, et jamais dans une adresse.

const NPI = /^\d{13}$/;
const ID = /^[A-Za-z0-9.-]{1,64}$/;

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

function moments(donnees: FormData, nom: string): Moment[] {
  return donnees.getAll(nom).filter((m): m is Moment => MOMENTS.includes(m as Moment));
}

/** L'id du patient du formulaire, ou retour à la recherche. */
function patientId(donnees: FormData): string {
  const id = texte(donnees, "patient_id");
  if (!ID.test(id)) redirect("/");
  return id;
}

const espace = (id: string, suite = "") => `/patients/${encodeURIComponent(id)}${suite}`;

/** Le NPI part une fois, dans le corps d'une requête ; l'écran suivant ne connaît que l'id du patient. */
export async function rechercher(donnees: FormData) {
  const npi = texte(donnees, "npi").replace(/\D/g, "");
  if (!NPI.test(npi)) redirect("/?erreur=npi");
  const reponse = await soin.rechercher(npi);
  if (reponse.statut === 404 || reponse.statut === 422) redirect("/?erreur=inconnu");
  if (reponse.statut !== 200 || !reponse.corps) redirect("/?erreur=service");
  redirect(espace(reponse.corps.patient_id));
}

export async function ouvrirCas(donnees: FormData) {
  const id = patientId(donnees);
  const motif = texte(donnees, "motif");
  if (!motif) redirect(espace(id, "?erreur=motif"));
  const reponse = await soin.ouvrirCas(id, motif);
  if (reponse.statut !== 201 || !reponse.corps) redirect(espace(id, "?erreur=cas"));
  redirect(espace(id, `/visite?cas=${encodeURIComponent(reponse.corps.cas_id)}`));
}

export async function cloreCas(donnees: FormData) {
  const id = patientId(donnees);
  const cas = texte(donnees, "cas");
  const reponse = await soin.clore(cas);
  const suite = reponse.statut === 200 ? "clos=1" : reponse.statut === 403 ? "erreur=cloture-relation" : "erreur=cloture";
  redirect(espace(id, `/cas?cas=${encodeURIComponent(cas)}&${suite}`));
}

export async function accesDUrgence(donnees: FormData) {
  const id = patientId(donnees);
  const motif = texte(donnees, "motif");
  const precision = texte(donnees, "precision");
  const raison = [motif, precision].filter(Boolean).join(" : ");
  if (raison.length < 10) redirect(espace(id, "?erreur=raison"));
  const reponse = await soin.urgence(id, raison);
  if (reponse.statut !== 201) redirect(espace(id, "?erreur=urgence"));
  redirect(espace(id, "?urgence=1"));
}

/** Le Document d'où l'entrée est reportée, s'il y en a un : `?document=` au retour, sur l'onglet Documents. */
function documentSource(donnees: FormData): string | undefined {
  const document = texte(donnees, "document_id");
  return ID.test(document) ? document : undefined;
}

/** Après une saisie : la synthèse, ou l'onglet Documents quand l'entrée est reportée d'un Document. */
function retour(id: string, document: string | undefined, suite: string): string {
  return document ? espace(id, `/documents?document=${encodeURIComponent(document)}&${suite}`) : espace(id, `?${suite}`);
}

export async function declarerAllergie(donnees: FormData) {
  const id = patientId(donnees);
  const document = documentSource(donnees);
  const [code, ...libelle] = texte(donnees, "allergie").split("|");
  if (!code) redirect(retour(id, document, "erreur=allergie"));
  const reponse = await soin.allergie(id, code, libelle.join("|"), document);
  redirect(retour(id, document, reponse.statut === 201 ? "ok=allergie" : "erreur=allergie"));
}

export type EtatDuDocument = { erreur?: string } | null;

const TYPES = new Set<string>(TYPES_DE_DOCUMENT.map(([code]) => code));
const FORMATS_DE_PAGE = new Set(["image/jpeg", "image/png", "application/pdf"]);

/**
 * Un Document que le patient a apporté : type, année, établissement d'origine, lisibilité et pages,
 * déjà compressées par le navigateur (ADR 0008). Le service l'écrit, origine `numerisation`.
 */
export async function ajouterDocument(_: EtatDuDocument, donnees: FormData): Promise<EtatDuDocument> {
  const id = patientId(donnees);
  const type = texte(donnees, "type");
  const annee = texte(donnees, "annee");
  const lisibilite = texte(donnees, "lisibilite");
  const etablissement = texte(donnees, "etablissement");
  const pages = donnees.getAll("pages").filter((p): p is File => typeof p !== "string" && p.size > 0);
  if (!TYPES.has(type)) return { erreur: "Choisissez le type du document." };
  if (!/^(19|20)\d{2}$/.test(annee)) return { erreur: "Donnez l’année du document, sur quatre chiffres." };
  if (lisibilite !== "lisible" && lisibilite !== "partiel") return { erreur: "Dites si le document est lisible." };
  if (pages.length === 0 || pages.length > 20) return { erreur: "Ajoutez entre une et vingt pages." };
  if (pages.some((p) => !FORMATS_DE_PAGE.has(p.type))) return { erreur: "Une page est une photo (JPEG, PNG) ou un PDF." };

  const envoi = new FormData();
  envoi.set("type", type);
  envoi.set("annee", annee);
  envoi.set("lisibilite", lisibilite);
  if (etablissement) envoi.set("etablissement", etablissement.slice(0, 200));
  for (const page of pages) envoi.append("pages", page, page.name);
  const reponse = await soin.ajouterDocument(id, envoi);
  if (reponse.statut === 413) return { erreur: "Trop lourd : au plus vingt pages de 3 Mo chacune." };
  if (reponse.statut === 422) return { erreur: "Le service a refusé ce document : vérifiez le type et le format des pages." };
  if (reponse.statut === 403) return { erreur: "Il faut une relation de soin avec ce patient pour ajouter un document." };
  if (reponse.statut !== 201 || !reponse.corps) return { erreur: "Le document n’a pas été enregistré. Réessayez." };
  redirect(espace(id, `/documents?document=${encodeURIComponent(reponse.corps.document_id)}&ok=document`));
}

export async function ajouterAntecedent(donnees: FormData) {
  const id = patientId(donnees);
  const document = documentSource(donnees);
  const type = texte(donnees, "type");
  const libelle = texte(donnees, "libelle");
  const depuis = texte(donnees, "depuis");
  const lien = texte(donnees, "lien");
  if (type !== "medical" && type !== "chirurgical" && type !== "familial") redirect(retour(id, document, "erreur=antecedent"));
  if (!libelle) redirect(retour(id, document, "erreur=antecedent"));
  if (type === "familial" && !LIENS_DE_PARENTE.some(([code]) => code === lien)) redirect(retour(id, document, "erreur=lien"));
  const reponse = await soin.antecedent(id, {
    type,
    libelle,
    ...(depuis && { depuis }),
    ...(type === "familial" ? { lien } : { actif: donnees.get("resolu") !== "on" }),
    ...(document && { document_id: document }),
  });
  redirect(retour(id, document, reponse.statut === 201 ? "ok=antecedent" : "erreur=antecedent"));
}

export async function ajouterTraitement(donnees: FormData) {
  const id = patientId(donnees);
  const produit = texte(donnees, "produit");
  const libelle = texte(donnees, "libelle");
  const posologie = texte(donnees, "posologie");
  if ((!produit && !libelle) || !posologie) redirect(espace(id, "?erreur=traitement"));
  const reponse = await soin.traitement(id, {
    ...(produit ? { produit } : { libelle }),
    posologie,
    moments: moments(donnees, "moments"),
  });
  redirect(espace(id, reponse.statut === 201 ? "?ok=traitement" : "?erreur=traitement"));
}

export async function arreterTraitement(donnees: FormData) {
  const id = patientId(donnees);
  const reponse = await soin.arreterTraitement(texte(donnees, "traitement"));
  redirect(espace(id, reponse.statut === 200 ? "?ok=arret" : "?erreur=traitement"));
}

export async function enregistrerGroupeSanguin(donnees: FormData) {
  const id = patientId(donnees);
  const valeur = texte(donnees, "groupe");
  if (!(GROUPES_SANGUINS as readonly string[]).includes(valeur)) redirect(espace(id, "?erreur=groupe"));
  const reponse = await soin.groupeSanguin(id, valeur);
  redirect(espace(id, reponse.statut === 200 ? "?ok=groupe" : "?erreur=groupe"));
}

export type EtatDeVisite = { erreur?: string; recu?: Recu } | null;

/**
 * Enregistre la visite, puis demande à identite le code carnet du reçu, pour le NPI que le bandeau
 * rend côté serveur. Le reçu revient à l'écran, jamais dans une adresse : ni le NPI ni le code carnet
 * ne figurent dans un journal.
 */
export async function enregistrerVisite(_: EtatDeVisite, donnees: FormData): Promise<EtatDeVisite> {
  const id = patientId(donnees);
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
      moments: moments(donnees, `l-${i}-moments`),
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

  const [bandeau, catalogue, session] = await Promise.all([soin.bandeau(id), soin.catalogue(), lireSession()]);
  const npi = bandeau.corps?.patient.npi;
  const code = npi ? await emettreCodeCarnet(npi) : null;
  const formes = new Map((catalogue.corps?.produits ?? []).map((p) => [p.code, p.forme ?? null]));
  const patient = bandeau.corps?.patient;
  return {
    recu: {
      numero: reponse.corps.numero_ordonnance,
      code,
      date: new Date().toISOString(),
      etablissement: session?.nom_etablissement ?? "",
      soignant: session?.nom ?? "",
      patient: patient ? `${patient.prenoms} ${patient.nom}` : texte(donnees, "patient"),
      lignes: ordonnance.map((l) => ({ ...l, unite: formes.get(l.produit) ?? null })),
    },
  };
}
