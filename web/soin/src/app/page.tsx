import { cookies } from "next/headers";
import { connection } from "next/server";

import { COOKIE_DE_SESSION, lireSante, lireSession, type Sante } from "../service";

function etatNoyau(sante: Sante | null): string {
  if (!sante) return "inconnu";
  if (sante.noyau.statut === "disponible") return `disponible, FHIR ${sante.noyau.version_fhir}`;
  return sante.noyau.statut;
}

export default async function Accueil() {
  // Rendue à chaque requête : la page montre l'état du moment, jamais celui de la construction.
  await connection();
  const jeton = (await cookies()).get(COOKIE_DE_SESSION)?.value;
  const [sante, session] = await Promise.all([lireSante(), jeton ? lireSession(jeton) : null]);

  return (
    <main>
      <p>Lafia</p>
      <h1>Soin</h1>
      <dl>
        <dt>Service soin</dt>
        <dd>{sante?.statut ?? "injoignable"}</dd>
        <dt>Noyau</dt>
        <dd>{etatNoyau(sante)}</dd>
        {session ? (
          <>
            <dt>Connecté comme</dt>
            <dd>{session.role}</dd>
            <dt>Établissement</dt>
            <dd>{session.etablissement}</dd>
          </>
        ) : (
          <>
            <dt>Session</dt>
            <dd>aucune</dd>
          </>
        )}
      </dl>
    </main>
  );
}
