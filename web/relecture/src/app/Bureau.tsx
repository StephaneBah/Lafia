// Le cadre de chaque écran de la relecture : l'en-tête, qui est connecté, et les écrans de refus.
import { adresseDuSite } from "@lafia/commun";
import { Alert, AppHeader, Button, Icon } from "@lafia/design";
import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { ACTEUR, TITRE } from "../libelles";
import { lireRelecteur, type Relecteur } from "../relecture";

/** Le relecteur connecté ; sans lui, l'accueil, qui dit l'état du service et mène à la connexion. */
export async function relecteurOuAccueil(): Promise<Relecteur> {
  const relecteur = await lireRelecteur();
  if (!relecteur) redirect("/");
  return relecteur;
}

/** Qui est connecté : rôle, nom et établissement, lus par identite. */
function Session({ relecteur }: { relecteur: Relecteur }) {
  return (
    <dl className="rel-session">
      <dt>Connecté comme</dt>
      <dd>{relecteur.role}</dd>
      <dt>Nom</dt>
      <dd>{relecteur.nom}</dd>
      <dt>Établissement</dt>
      <dd>{relecteur.nom_etablissement}</dd>
    </dl>
  );
}

export async function Bureau({
  relecteur,
  titre,
  retour,
  large,
  children,
}: {
  relecteur: Relecteur;
  titre: string;
  /** Un lien vers « Ma semaine » au-dessus du titre, sur les écrans d'une tâche. */
  retour?: boolean;
  /** Les écrans d'une tâche prennent toute la largeur : les pages s'y lisent en grand. */
  large?: boolean;
  children: ReactNode;
}) {
  return (
    <>
      <AppHeader
        actor={ACTEUR}
        actorLabel={TITRE}
        siteHref={await adresseDuSite()}
        place={relecteur.nom_etablissement}
        user={relecteur.nom}
        signOut
      />
      <main className={large ? "lf-app-main rel-main rel-main--large" : "lf-app-main rel-main"}>
        {retour && (
          <a className="rel-retour" href="/">
            <Icon name="arrow-left" size={20} />
            <span>Ma semaine</span>
          </a>
        )}
        <div className="rel-entete">
          <h1 className="lf-app-titre">{titre}</h1>
          <Session relecteur={relecteur} />
        </div>
        {children}
      </main>
    </>
  );
}

/** Pourquoi un écran ne s'ouvre pas, d'après le statut que rend le service, et par où continuer. */
export function Refus({ statut, ici }: { statut: number; ici: string }) {
  if (statut === 0 || statut >= 500) {
    return (
      <Alert
        tone="danger"
        title="Le service relecture ne répond pas."
        actions={
          <Button href={ici} size="pro" variant="secondary" icon="arrow-left">
            Réessayer
          </Button>
        }
      >
        Rien n'est perdu : les tâches déjà faites sont enregistrées. Réessayez dans un instant.
      </Alert>
    );
  }
  if (statut === 403) {
    return (
      <Alert
        tone="attention"
        title="Cette tâche ne vous est pas confiée."
        actions={
          <Button href="/" size="pro" icon="list">
            Revenir à ma semaine
          </Button>
        }
      >
        Chaque tâche est confiée à une seule personne. La Relecture et le Contrôle reviennent aux agents de relecture
        (jamais le Contrôle de sa propre Relecture), la validation aux médecins et aux infirmiers.
      </Alert>
    );
  }
  return (
    <Alert
      tone="attention"
      title="Cette tâche n'est plus disponible."
      actions={
        <Button href="/" size="pro" icon="list">
          Revenir à ma semaine
        </Button>
      }
    >
      Elle a pu être faite par quelqu'un d'autre, changer d'étape, ou revenir au lot commun à la fin de la semaine.
    </Alert>
  );
}
