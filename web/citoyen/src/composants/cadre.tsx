// Le cadre des écrans du carnet : l'en-tête citoyen, le retour au carnet, et ce que dit un écran quand
// le carnet ne s'ouvre pas. Composants serveur : les illustrations restent hors du JavaScript envoyé.

import { AppHeader, Button, Icon } from "@lafia/design";
import { Illustration } from "@lafia/design/illustration";
import { adresseDuSite } from "../lib/site";
import type { ReactNode } from "react";

import type { Lecture } from "../lib/carnet";

export async function Cadre({ children, connecte = true }: { children: ReactNode; connecte?: boolean }) {
  const site = await adresseDuSite();
  return (
    <>
      <AppHeader actor="citoyen" actorLabel="Mon carnet" siteHref={site} signOut={connecte} />
      <main className="lf-app-main lf-app-main--citoyen carnet">{children}</main>
    </>
  );
}

/** Le retour au carnet : une flèche et un mot, assez grand pour un pouce. */
export function Retour({ href = "/", children = "Mon carnet" }: { href?: string; children?: ReactNode }) {
  return (
    <a className="carnet-retour" href={href}>
      <Icon name="arrow-left" size={22} />
      <span>{children}</span>
    </a>
  );
}

/** Un état vide ou un moment clé : l'illustration porte le sens, une phrase le dit. */
export function Scene({
  illustration,
  titre,
  children,
}: {
  illustration: Parameters<typeof Illustration>[0]["name"];
  titre: string;
  children?: ReactNode;
}) {
  return (
    <section className="carnet-scene">
      <div className="carnet-scene-illu">
        <Illustration name={illustration} decorative />
      </div>
      <p className="carnet-grand">{titre}</p>
      {children}
    </section>
  );
}

/** Ce que montre un écran quand le carnet n'a pas été lu : se connecter, ou réessayer. */
export function CarnetNonLu({ lecture }: { lecture: Exclude<Lecture<unknown>, { etat: "lu" }> }) {
  if (lecture.etat === "sans-session") {
    return (
      <Scene illustration="vide-session" titre="Ouvrez votre carnet avec votre NPI et votre code carnet.">
        <Button href="/connexion" icon="lock-simple" size="citizen" block>
          Ouvrir mon carnet
        </Button>
      </Scene>
    );
  }
  if (lecture.etat === "introuvable") {
    return (
      <Scene illustration="vide-cas" titre="Aucun dossier n'existe encore pour vous.">
        <p className="carnet-doux">Il s'ouvrira à votre première visite dans un centre de santé.</p>
      </Scene>
    );
  }
  return (
    <Scene illustration="vide-session" titre="Votre carnet ne répond pas pour le moment.">
      <p className="carnet-doux">Réessayez dans un instant : rien de votre dossier n'est perdu.</p>
    </Scene>
  );
}
