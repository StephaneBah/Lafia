import path from "node:path";
import type { NextConfig } from "next";

const configuration: NextConfig = {
  // Image autonome : le serveur et les seuls modules qu'il utilise.
  output: "standalone",
  // Racine de l'espace de travail web/ : les dépendances y sont hissées, les paquets partagés y vivent.
  outputFileTracingRoot: path.join(import.meta.dirname, ".."),
  // Le code commun et le système de design sont compilés dans l'application, jamais chargés à l'exécution.
  transpilePackages: ["@lafia/commun", "@lafia/design"],
  // Un Document apporté par le patient part du navigateur droit au service soin, par la passerelle
  // (composants/AjouterUnDocument.tsx) : aucune action serveur ne porte de pages, la limite par défaut
  // des actions serveur suffit.
};

export default configuration;
