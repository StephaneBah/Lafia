import "@lafia/design/styles.css";
import "./carnet.css";

import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Lafia · Mon carnet",
};

export const viewport: Viewport = { width: "device-width", initialScale: 1 };

export default function MiseEnPage({ children }: { children: ReactNode }) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
