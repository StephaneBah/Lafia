"use server";

// Ce que les écrans du navigateur demandent au service relecture, par le serveur de l'application : le
// cookie de session reste ici, jamais lu par le navigateur. Chaque action rend un objet simple : ce qui
// est enregistré, ou le statut du refus, que l'écran dit en mots.
import { redirect } from "next/navigation";

import {
  confirmer,
  controler,
  declarerInutilisable,
  enregistrer,
  tacheSuivante,
  valider,
  type Decision,
} from "../relecture";

/** Un refus : le statut du service (0 : injoignable, 401 : session à renouveler). */
export type Refus = { ok: false; statut: number };

export type IssueDEnregistrement = { ok: true; version: string } | Refus;

/** Le brouillon du relecteur, à la version qu'il a lue. 409 : enregistré ailleurs depuis ; 422 : trop long. */
export async function enregistrerLeBrouillon(tache: string, markdown: string, version: string): Promise<IssueDEnregistrement> {
  const reponse = await enregistrer(tache, markdown, version);
  if (!reponse.ok) return { ok: false, statut: reponse.statut };
  return { ok: true, version: reponse.corps.version };
}

/** Où mener après une tâche faite : la suivante de la semaine, ou `null` pour « Ma semaine ». */
export type Suite = { ok: true; suivante: string | null };

export type IssueDeConfirmation =
  | Suite
  | (Refus & { erreurs?: string[]; nonVerifies?: number[]; message?: string });

/** La double confirmation : les volets cochés et le résumé des changements. */
export async function confirmerLaTranscription(tache: string, voletsVerifies: number[], resume: string): Promise<IssueDeConfirmation> {
  const reponse = await confirmer(tache, voletsVerifies, resume.trim());
  if (!reponse.ok) {
    const detail = reponse.detail as { erreurs?: string[]; volets_non_verifies?: number[]; message?: string } | string | undefined;
    if (detail && typeof detail === "object") {
      return { ok: false, statut: reponse.statut, erreurs: detail.erreurs, nonVerifies: detail.volets_non_verifies, message: detail.message };
    }
    return { ok: false, statut: reponse.statut, message: typeof detail === "string" ? detail : undefined };
  }
  return { ok: true, suivante: await tacheSuivante(tache) };
}

/** Le Contrôle : accepter la Transcription, ou la renvoyer au relecteur avec une note. */
export async function controlerLaTranscription(tache: string, decision: "accepter" | "renvoyer", note: string): Promise<Suite | Refus> {
  const propre = note.trim();
  if (decision === "renvoyer" && !propre) return { ok: false, statut: 422 };
  const reponse = await controler(tache, decision, propre || undefined);
  if (!reponse.ok) return { ok: false, statut: reponse.statut };
  return { ok: true, suivante: await tacheSuivante(tache) };
}

/** Un Document qui n'est pas médical, ou déjà numérisé : la Relecture est close sans Transcription. */
export async function declarerLeDocumentInutilisable(tache: string, raison: "non-medical" | "doublon"): Promise<Suite | Refus> {
  if (raison !== "non-medical" && raison !== "doublon") return { ok: false, statut: 422 };
  const reponse = await declarerInutilisable(tache, raison);
  if (!reponse.ok) return { ok: false, statut: reponse.statut };
  return { ok: true, suivante: await tacheSuivante(tache) };
}

/** Ce que rend la validation : la tâche suivante quand tout est parti, ou pourquoi rien n'est parti. */
export type IssueDeLaValidation =
  | { validee: true; suivante: string | null }
  | { validee: false; erreur: "incomplet" | "service" | "indisponible" | "refusee" }
  | null;

const DECISIONS = new Set(["accepter", "corriger", "rejeter"]);

/**
 * Toutes les décisions du soignant, envoyées ensemble. Le service écrit au dossier ce qui est accepté
 * ou corrigé, avec origine extraction et sa Provenance ; le rejeté reste dans la tâche.
 */
export async function validerLaTache(_precedent: IssueDeLaValidation, formulaire: FormData): Promise<IssueDeLaValidation> {
  const tache = String(formulaire.get("tache") ?? "");
  let decisions: Decision[];
  try {
    decisions = JSON.parse(String(formulaire.get("decisions") ?? "[]")) as Decision[];
  } catch {
    return { validee: false, erreur: "incomplet" };
  }
  const completes = decisions.every(
    (d) => typeof d.id === "string" && DECISIONS.has(d.decision) && (d.decision !== "corriger" || Boolean(d.valeur?.trim())),
  );
  if (!completes) return { validee: false, erreur: "incomplet" };

  const reponse = await valider(
    tache,
    decisions.map((d) => (d.decision === "corriger" ? { id: d.id, decision: d.decision, valeur: d.valeur!.trim() } : { id: d.id, decision: d.decision })),
  );
  if (!reponse.ok) {
    if (reponse.statut === 401) redirect("/connexion");
    if (reponse.statut === 0 || reponse.statut >= 500) return { validee: false, erreur: "service" };
    if (reponse.statut === 422 || reponse.statut === 400) return { validee: false, erreur: "refusee" };
    return { validee: false, erreur: "indisponible" };
  }
  return { validee: true, suivante: await tacheSuivante(tache) };
}
