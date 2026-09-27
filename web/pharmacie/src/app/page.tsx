import "./comptoir.css";

import { COOKIE_DE_SESSION, EtatDeLActeur, adresseDuSite, identiteParLaPasserelle } from "@lafia/commun";
import { AppHeader } from "@lafia/design";
import { cookies } from "next/headers";
import { connection } from "next/server";

import { Comptoir } from "./Comptoir";
import { Officine } from "./Officine";

/**
 * Le comptoir de la pharmacie d'un établissement : le pharmacien tape ou scanne le numéro d'ordonnance,
 * voit ce qui reste à remettre, et le remet. L'officine, connectée sous son nom, vérifie l'ordonnance et
 * déclare ce qu'elle a vendu. Sans l'une de ces sessions, l'état de l'acteur et la connexion.
 */
export default async function Accueil() {
  await connection();
  const jeton = (await cookies()).get(COOKIE_DE_SESSION)?.value;
  const session = jeton ? await identiteParLaPasserelle().lireSession(jeton) : null;
  if (session?.role === "officine") {
    return (
      <>
        <AppHeader actor="pharmacie" actorLabel="Officine" siteHref={await adresseDuSite()} place={session.nom} signOut />
        <main className="lf-app-main">
          <dl className="pharmacie-session">
            <dt>Connecté comme</dt>
            <dd>{session.role}</dd>
            <dt>Officine</dt>
            <dd>{session.nom}</dd>
          </dl>
          <Officine />
        </main>
      </>
    );
  }
  if (!session || session.role !== "pharmacien") {
    return <EtatDeLActeur titre="Pharmacie" service="pharmacie" avecConnexion />;
  }
  return (
    <>
      <AppHeader
        actor="pharmacie"
        actorLabel="Pharmacie"
        siteHref={await adresseDuSite()}
        place={session.nom_etablissement}
        user={session.nom}
        signOut
      />
      <main className="lf-app-main">
        <dl className="pharmacie-session">
          <dt>Connecté comme</dt>
          <dd>{session.role}</dd>
          <dt>Nom</dt>
          <dd>{session.nom}</dd>
          <dt>Établissement</dt>
          <dd>{session.nom_etablissement}</dd>
        </dl>
        <Comptoir />
      </main>
    </>
  );
}
