import { AppHeader, Button, Card, Icon, type Acteur } from "@lafia/design";
import { cookies } from "next/headers";
import { connection } from "next/server";
import type { ReactNode } from "react";

import {
  COOKIE_DE_SESSION,
  identiteParLaPasserelle,
  serviceParLaPasserelle,
  type Sante,
  type Session,
} from "./service";
import { adresseDuSite } from "./site";

/** Une valeur d'état : une coche quand tout répond, un avertissement sinon ; le mot dit toujours l'état. */
function Etat({ bon, children }: { bon: boolean; children: ReactNode }) {
  return (
    <span className={bon ? "lf-etat-valeur is-bon" : "lf-etat-valeur is-mauvais"}>
      <Icon name={bon ? "check" : "warning"} size={18} />
      <span>{children}</span>
    </span>
  );
}

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
  service: Acteur;
  avecConnexion?: boolean;
}) {
  // Rendu à chaque requête : la page montre l'état du moment, jamais celui de la construction.
  await connection();
  const jeton = (await cookies()).get(COOKIE_DE_SESSION)?.value;
  const [sante, session, site] = await Promise.all([
    serviceParLaPasserelle(service).lireSante(),
    jeton ? identiteParLaPasserelle().lireSession(jeton) : null,
    adresseDuSite(),
  ]);
  const citoyen = service === "citoyen";

  return (
    <>
      {/* La déconnexion est un formulaire de l'en-tête, pas un lien : identite n'accepte la déconnexion
          que des pages de l'application. */}
      <AppHeader
        actor={service}
        actorLabel={titre}
        siteHref={site}
        place={session && "nom_etablissement" in session ? session.nom_etablissement : undefined}
        user={session && "nom" in session ? session.nom : undefined}
        signOut={avecConnexion && Boolean(session)}
      />
      <main className={citoyen ? "lf-app-main lf-app-main--citoyen" : "lf-app-main"}>
        <Card className="lf-etat-carte">
          <h1 className="lf-app-titre">{titre}</h1>
          <dl className="lf-etat">
            <dt>{`Service ${service}`}</dt>
            <dd>
              <Etat bon={sante?.statut === "disponible"}>{sante?.statut ?? "injoignable"}</Etat>
            </dd>
            <dt>Noyau</dt>
            <dd>
              <Etat bon={sante?.noyau.statut === "disponible"}>{etatNoyau(sante)}</Etat>
            </dd>
            {session ? (
              <Porteur session={session} />
            ) : (
              <>
                <dt>Session</dt>
                <dd>aucune</dd>
              </>
            )}
          </dl>
          {avecConnexion && !session && (
            <Button href="/connexion" icon="lock-simple" size={citoyen ? "citizen" : "pro"}>
              Se connecter
            </Button>
          )}
        </Card>
      </main>
    </>
  );
}
