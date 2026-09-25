import path from "node:path";
import type { NextConfig } from "next";

const configuration: NextConfig = {
  // Image autonome : le serveur et les seuls modules qu'il utilise.
  output: "standalone",
  // Racine de l'espace de travail web/ : les dépendances y sont hissées, le système de design y vit.
  outputFileTracingRoot: path.join(import.meta.dirname, ".."),
  // Le système de design est compilé dans l'application, jamais chargé à l'exécution.
  transpilePackages: ["@lafia/design"],
};

export default configuration;
