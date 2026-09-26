import { cookies } from "next/headers";
import { connection } from "next/server";

import { COOKIE_DE_SESSION, serviceParLaPasserelle, type Sante } from "./service";

function etatNoyau(sante: Sante | null): string {
  if (!sante) return "inconnu";
  if (sante.noyau.statut === "disponible") return `disponible, FHIR ${sante.noyau.version_fhir}`;
  return sante.noyau.statut;
}

/**
 * L'accueil d'une application au socle : le nom de son acteur, l'état de son service et du noyau
 * derrière lui, et l'agent connecté, que le service lit du cookie de session.
 */
export async function EtatDeLActeur({ titre, service }: { titre: string; service: string }) {
  // Rendu à chaque requête : la page montre l'état du moment, jamais celui de la construction.
  await connection();
  const jeton = (await cookies()).get(COOKIE_DE_SESSION)?.value;
  const client = serviceParLaPasserelle(service);
  const [sante, session] = await Promise.all([
    client.lireSante(),
    jeton ? client.lireSession(jeton) : null,
  ]);

  return (
    <main>
      <p>Lafia</p>
      <h1>{titre}</h1>
      <dl>
        <dt>{`Service ${service}`}</dt>
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
