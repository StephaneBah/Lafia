import { headers } from "next/headers";

/** L'adresse du site produit : l'hôte de la page sans le sous-domaine de l'application (comme @lafia/commun). */
export async function adresseDuSite(): Promise<string> {
  const hote = ((await headers()).get("host") ?? "").replace(/:\d+$/, "");
  const domaine = hote.split(".").slice(1).join(".") || "localhost";
  return `https://${domaine}`;
}
