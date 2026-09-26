import path from "node:path";
import type { NextConfig } from "next";

const configuration: NextConfig = {
  // Image autonome : le serveur et les seuls modules qu'il utilise.
  output: "standalone",
  // Racine de l'espace de travail web/ : les dépendances y sont hissées, les paquets partagés y vivent.
  outputFileTracingRoot: path.join(import.meta.dirname, ".."),
  // Le code commun et le système de design sont compilés dans l'application, jamais chargés à l'exécution.
  transpilePackages: ["@lafia/commun", "@lafia/design"],
};

export default configuration;
