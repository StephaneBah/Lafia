import { headers } from "next/headers";

/**
 * L'adresse du site produit, sur le domaine lui-même : l'hôte de la page sans le sous-domaine de
 * l'application. La passerelle ne mène à une application que par `<acteur>.<domaine>` : cet hôte-là.
 */
export async function adresseDuSite(): Promise<string> {
  const hote = ((await headers()).get("host") ?? "").replace(/:\d+$/, "");
  const domaine = hote.split(".").slice(1).join(".") || "localhost";
  return `https://${domaine}`;
}
