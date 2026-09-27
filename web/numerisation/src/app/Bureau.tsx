// Le cadre de chaque écran du bureau : l'en-tête, qui est connecté, et l'étape où l'on en est.
import { adresseDuSite } from "@lafia/commun";
import { AppHeader, Icon } from "@lafia/design";
import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { ACTEUR, TITRE } from "../libelles";
import { lireAgent, type Agent } from "../numerisation";

const ETAPES = ["Accueillir", "Confirmer l'identité", "Numériser", "Dépôt"];

/** L'agent connecté ; sans lui, l'accueil, qui dit l'état du service et mène à la connexion. */
export async function agentOuAccueil(): Promise<Agent> {
  const agent = await lireAgent();
  if (!agent) redirect("/");
  return agent;
}

/** Qui est connecté : rôle, nom et établissement, lus par identite. */
function Session({ agent }: { agent: Agent }) {
  return (
    <dl className="num-session">
      <dt>Connecté comme</dt>
      <dd>{agent.role}</dd>
      <dt>Nom</dt>
      <dd>{agent.nom}</dd>
      <dt>Établissement</dt>
      <dd>{agent.nom_etablissement}</dd>
    </dl>
  );
}

/** Les quatre étapes du bureau ; celle en cours est marquée par sa pastille et par `aria-current`. */
function Etapes({ etape }: { etape: number }) {
  return (
    <ol className="num-etapes" aria-label="Étapes du dépôt">
      {ETAPES.map((nom, i) => {
        const rang = i + 1;
        const etat = rang < etape ? "is-faite" : rang === etape ? "is-en-cours" : "";
        return (
          <li key={nom} className={etat} aria-current={rang === etape ? "step" : undefined}>
            <span className="num-etape-pastille" aria-hidden="true">
              {rang < etape ? <Icon name="check" size={18} /> : rang}
            </span>
            <span>{nom}</span>
          </li>
        );
      })}
    </ol>
  );
}

export async function Bureau({
  agent,
  etape,
  titre,
  children,
}: {
  agent: Agent;
  etape?: number;
  titre: string;
  children: ReactNode;
}) {
  return (
    <>
      <AppHeader
        actor={ACTEUR}
        actorLabel={TITRE}
        siteHref={await adresseDuSite()}
        place={agent.nom_etablissement}
        user={agent.nom}
        signOut
      />
      <main className="lf-app-main num-main">
        <div className="num-entete">
          <h1 className="lf-app-titre">{titre}</h1>
          <Session agent={agent} />
        </div>
        {etape && <Etapes etape={etape} />}
        {children}
      </main>
    </>
  );
}
