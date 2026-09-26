import { cookies } from "next/headers";
import { connection } from "next/server";

import {
  COOKIE_DE_SESSION,
  identiteParLaPasserelle,
  serviceParLaPasserelle,
  type Sante,
  type Session,
} from "./service";

function etatNoyau(sante: Sante | null): string {
  if (!sante) return "inconnu";
  if (sante.noyau.statut === "disponible") return `disponible, FHIR ${sante.noyau.version_fhir}`;
  return sante.noyau.statut;
}

/** Qui est connecté : le rôle ; pour un agent, son nom et son établissement ; pour une officine, son nom. */
function Porteur({ session }: { session: Session }) {
  return (
    <>
      <dt>Connecté comme</dt>
      <dd>{session.role}</dd>
      {"nom" in session && (
        <>
          <dt>Nom</dt>
          <dd>{session.nom}</dd>
        </>
      )}
      {"nom_etablissement" in session && (
        <>
          <dt>Établissement</dt>
          <dd>{session.nom_etablissement}</dd>
        </>
      )}
    </>
  );
}

/**
 * L'accueil d'une application : le nom de son acteur, l'état de son service et du noyau derrière
 * lui, et qui est connecté, qu'identite lit du cookie de session. Une application où l'on se
 * connecte (`avecConnexion`) mène à sa page de connexion sans session, et offre la déconnexion avec.
 */
export async function EtatDeLActeur({
  titre,
  service,
  avecConnexion = false,
}: {
  titre: string;
  service: string;
  avecConnexion?: boolean;
}) {
  // Rendu à chaque requête : la page montre l'état du moment, jamais celui de la construction.
  await connection();
  const jeton = (await cookies()).get(COOKIE_DE_SESSION)?.value;
  const [sante, session] = await Promise.all([
    serviceParLaPasserelle(service).lireSante(),
    jeton ? identiteParLaPasserelle().lireSession(jeton) : null,
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
          <Porteur session={session} />
        ) : (
          <>
            <dt>Session</dt>
            <dd>aucune</dd>
          </>
        )}
      </dl>
      {avecConnexion &&
        (session ? (
          // Un formulaire, pas un lien : identite n'accepte la déconnexion que des pages de l'application.
          <form method="post" action="/api/identite/deconnexion">
            <button type="submit">Se déconnecter</button>
          </form>
        ) : (
          <p>
            <a href="/connexion">Se connecter</a>
          </p>
        ))}
    </main>
  );
}
