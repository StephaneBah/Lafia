import "./comptoir.css";

import { COOKIE_DE_SESSION, EtatDeLActeur, adresseDuSite, identiteParLaPasserelle } from "@lafia/commun";
import { AppHeader } from "@lafia/design";
import { cookies } from "next/headers";
import { connection } from "next/server";

import { Comptoir } from "./Comptoir";

/**
 * Le comptoir de la pharmacie d'un établissement : le pharmacien tape le numéro d'ordonnance, voit ce
 * qui reste à remettre, et le remet. Sans session de pharmacien, l'état de l'acteur et la connexion.
 */
export default async function Accueil() {
  await connection();
  const jeton = (await cookies()).get(COOKIE_DE_SESSION)?.value;
  const session = jeton ? await identiteParLaPasserelle().lireSession(jeton) : null;
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
        <Comptoir />
      </main>
    </>
  );
}
