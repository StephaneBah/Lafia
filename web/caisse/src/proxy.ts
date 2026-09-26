// Avant chaque page : renouvelle le jeton expiré tant que la session tient (@lafia/commun).
export { renouvelerLaSession as proxy } from "@lafia/commun/renouvellement";

export const config = {
  // Les pages seulement, pas les fichiers que Next.js sert lui-même.
  matcher: ["/((?!_next/|favicon.ico).*)"],
};
