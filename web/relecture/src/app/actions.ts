"use server";

import { redirect } from "next/navigation";

import { ANNEE_MIN, TYPES_DE_DOCUMENT, VERDICTS } from "../libelles";
import { tacheSuivante, trier, valider, type Decision, type Verdict } from "../relecture";

/** Pourquoi le verdict n'est pas parti ; ce qui a été choisi reste à l'écran. */
export type RefusDuTriage = { erreur: "annee" | "type" | "verdict" | "service" | "indisponible" } | null;

/** Où mène une tâche faite : la suivante de la semaine, ou « Ma semaine » quand il n'y en a plus. */
async function allerALaSuivante(tache: string, fait: string): Promise<never> {
  const suivante = await tacheSuivante(tache);
  redirect(suivante ? `/taches/${encodeURIComponent(suivante)}?fait=${fait}` : `/?fait=${fait}`);
}

/** Le verdict de triage d'une tâche, puis tout de suite la tâche suivante. */
export async function trierLaTache(_precedent: RefusDuTriage, formulaire: FormData): Promise<RefusDuTriage> {
  const tache = String(formulaire.get("tache") ?? "");
  const verdict = String(formulaire.get("verdict") ?? "");
  const type = String(formulaire.get("type") ?? "");
  const annee = String(formulaire.get("annee") ?? "").trim();

  if (!VERDICTS.some((v) => v.code === verdict)) return { erreur: "verdict" };
  if (verdict === "mauvais-type" && !TYPES_DE_DOCUMENT.some((t) => t.code === type)) return { erreur: "type" };
  if (annee && (!/^\d{4}$/.test(annee) || Number(annee) < ANNEE_MIN || Number(annee) > new Date().getFullYear())) {
    return { erreur: "annee" };
  }

  const reponse = await trier(tache, {
    verdict: verdict as Verdict,
    ...(verdict === "mauvais-type" ? { type } : {}),
    ...(annee ? { annee: Number(annee) } : {}),
  });
  if (!reponse.ok) {
    if (reponse.statut === 401) redirect("/connexion");
    if (reponse.statut === 422) return { erreur: "verdict" };
    if (reponse.statut === 0 || reponse.statut >= 500) return { erreur: "service" };
    return { erreur: "indisponible" };
  }
  return allerALaSuivante(tache, "triage");
}

/** Ce que rend la validation : la tâche suivante quand tout est parti, ou pourquoi rien n'est parti. */
export type IssueDeLaValidation =
  | { validee: true; suivante: string | null }
  | { validee: false; erreur: "incomplet" | "service" | "indisponible" | "refusee" }
  | null;

const DECISIONS = new Set(["accepter", "corriger", "rejeter"]);

/**
 * Toutes les décisions de la tâche, envoyées ensemble. Le service écrit au dossier ce qui est accepté
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
