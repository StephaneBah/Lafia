import { connection } from "next/server";

import { identiteParLaPasserelle, type CompteDeDemonstration } from "./service";

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

/**
 * La page de connexion des agents et des officines. Le formulaire va droit à identite, par la
 * passerelle : l'application ne voit jamais le mot de passe, ni le jeton qu'identite pose en retour.
 * Elle liste les comptes de démonstration de son application, avec leurs mots de passe, publics.
 */
export async function PageDeConnexion({ titre, searchParams }: { titre: string } & ParametresDePage) {
  await connection();
  const [{ erreur }, comptes] = await Promise.all([
    searchParams,
    identiteParLaPasserelle().lireComptesDeDemonstration(),
  ]);
  const comptesDAgents = (comptes ?? []).filter(
    (compte): compte is CompteDeDemonstration => "identifiant" in compte,
  );
  const message = typeof erreur === "string" ? MESSAGES_DE_REFUS[erreur] : undefined;

  return (
    <main>
      <p>Lafia</p>
      <h1>{titre}</h1>
      <h2>Connexion</h2>
      {message && <p role="alert">{message}</p>}
      <form method="post" action="/api/identite/connexion">
        <p>
          <label>
            Identifiant <input name="identifiant" autoComplete="username" required />
          </label>
        </p>
        <p>
          <label>
            Mot de passe <input name="mot_de_passe" type="password" autoComplete="current-password" required />
          </label>
        </p>
        <button type="submit">Se connecter</button>
      </form>
      <h2>Comptes de démonstration</h2>
      <table>
        <thead>
          <tr>
            <th>Identifiant</th>
            <th>Mot de passe</th>
            <th>Rôle</th>
            <th>Établissement ou officine</th>
          </tr>
        </thead>
        <tbody>
          {comptesDAgents.map((compte) => (
            <tr key={compte.identifiant}>
              <td>{compte.identifiant}</td>
              <td>{compte.mot_de_passe}</td>
              <td>{compte.role}</td>
              <td>{compte.structure}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
