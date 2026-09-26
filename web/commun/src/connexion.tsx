import { Alert, AppHeader, Button, Card, Table, TextInput, type Acteur } from "@lafia/design";
import { connection } from "next/server";

import { identiteParLaPasserelle, type CompteDeDemonstration } from "./service";
import { adresseDuSite } from "./site";
import { UtiliserCeCompte } from "./UtiliserCeCompte";

/** Ce que la page dit de chaque refus que rend identite (`/connexion?erreur=…`). */
const MESSAGES_DE_REFUS: Record<string, string> = {
  identifiants: "Identifiant ou mot de passe incorrect.",
  application: "Ce compte n'ouvre pas cette application.",
  verrouille: "Trop d'essais : réessayez dans 15 minutes.",
};

/** Ce que Next.js passe à une page : ses paramètres d'adresse, `?erreur=…` pour la page de connexion. */
export type ParametresDePage = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

const FORMULAIRE = "formulaire-de-connexion";

/**
 * La page de connexion des agents et des officines. Le formulaire va droit à identite, par la
 * passerelle : l'application ne voit jamais le mot de passe, ni le jeton qu'identite pose en retour.
 * Elle liste les comptes de démonstration de son application, avec leurs mots de passe, publics ;
 * « Utiliser » en remplit le formulaire.
 */
export async function PageDeConnexion({
  acteur,
  titre,
  searchParams,
}: { acteur: Acteur; titre: string } & ParametresDePage) {
  await connection();
  const [{ erreur }, comptes, site] = await Promise.all([
    searchParams,
    identiteParLaPasserelle().lireComptesDeDemonstration(),
    adresseDuSite(),
  ]);
  const comptesDAgents = (comptes ?? []).filter(
    (compte): compte is CompteDeDemonstration => "identifiant" in compte,
  );
  const message = typeof erreur === "string" ? MESSAGES_DE_REFUS[erreur] : undefined;

  return (
    <>
      <AppHeader actor={acteur} actorLabel={titre} siteHref={site} />
      <main className="lf-app-main lf-connexion">
        <Card className="lf-connexion-carte">
          <h1 className="lf-app-titre">Connexion</h1>
          <p className="lf-app-sous-titre">{`Votre identifiant et votre mot de passe ouvrent l'application ${titre}.`}</p>
          {message && <Alert tone="danger" title={message} />}
          <form id={FORMULAIRE} className="lf-formulaire" method="post" action="/api/identite/connexion">
            <TextInput label="Identifiant" name="identifiant" autoComplete="username" icon="user" size="pro" required autoFocus />
            <TextInput
              label="Mot de passe"
              name="mot_de_passe"
              type="password"
              autoComplete="current-password"
              icon="lock-simple"
              size="pro"
              required
            />
            <Button type="submit" size="pro" block>
              Se connecter
            </Button>
          </form>
        </Card>
        <Card className="lf-connexion-demo">
          <h2 className="lf-app-sous-titre-fort">Comptes de démonstration</h2>
          <p className="lf-app-note">Publics : toutes les données sont fictives. N'y saisissez aucune donnée réelle.</p>
          <Table
            dense
            columns={[
              { key: "identifiant", label: "Identifiant", mono: true },
              { key: "motDePasse", label: "Mot de passe", mono: true },
              { key: "role", label: "Rôle" },
              { key: "structure", label: "Établissement ou officine" },
              { key: "action", label: "Formulaire" },
            ]}
            rows={comptesDAgents.map((compte) => ({
              id: compte.identifiant,
              identifiant: compte.identifiant,
              motDePasse: compte.mot_de_passe,
              role: compte.role,
              structure: compte.structure,
              action: <UtiliserCeCompte formulaire={FORMULAIRE} identifiant={compte.identifiant} motDePasse={compte.mot_de_passe} />,
            }))}
            empty="Aucun compte de démonstration : identite ne répond pas."
          />
        </Card>
      </main>
    </>
  );
}
