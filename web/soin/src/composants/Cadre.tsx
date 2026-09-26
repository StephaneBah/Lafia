import { AppHeader, Button } from "@lafia/design";
import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { domaine, lireSession } from "../lib/soin";
import type { SessionSoignant } from "../lib/types";

/** Le soignant connecté, ou la page de connexion. */
export async function soignantConnecte(): Promise<SessionSoignant> {
  const session = await lireSession();
  if (!session) redirect("/connexion");
  return session;
}

/** L'en-tête de l'application soin, l'établissement et le soignant, puis l'écran. */
export async function Cadre({
  session,
  retour,
  children,
}: {
  session: SessionSoignant;
  retour?: { href: string; libelle: string };
  children: ReactNode;
}) {
  const site = `https://${await domaine()}`;
  return (
    <>
      <AppHeader actor="soin" actorLabel="Soin" siteHref={site} place={session.nom_etablissement} user={session.nom} signOut />
      <main className="lf-app-main sn-main">
        {retour && (
          <div className="sn-retour">
            <Button href={retour.href} size="pro" variant="ghost" icon="arrow-left">
              {retour.libelle}
            </Button>
          </div>
        )}
        {children}
      </main>
    </>
  );
}
