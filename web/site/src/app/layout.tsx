import "@lafia/design/styles.css";
import "./site.css";

import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Lafia · Votre dossier de santé vous suit, partout au Bénin",
  description:
    "Lafia : un dossier de santé par citoyen béninois, retrouvé par son seul NPI, d'un centre de santé à l'autre, de la caisse à la pharmacie.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  themeColor: "#3648C0",
};

export default function MiseEnPage({ children }: { children: ReactNode }) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
