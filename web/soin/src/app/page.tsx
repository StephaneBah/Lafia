import { EtatDeLActeur, type ParametresDePage } from "@lafia/commun";
import { Alert, Button, Card } from "@lafia/design";
import { connection } from "next/server";

import { ChampNpi } from "../composants/ChampNpi";
import { Cadre } from "../composants/Cadre";
import { lireSession } from "../lib/soin";
import { rechercher } from "./actions";

/** Sans session : l'état de l'application et la connexion. Avec : la recherche d'un patient par NPI, qui ne passe par aucune adresse. */
export default async function Accueil({ searchParams }: ParametresDePage) {
  await connection();
  const session = await lireSession();
  if (!session) return <EtatDeLActeur titre="Soin" service="soin" avecConnexion />;
  const { erreur } = await searchParams;

  return (
    <Cadre session={session}>
      <div className="sn-recherche">
        <Card className="sn-panneau">
          <h1 className="lf-app-titre">Rechercher un patient</h1>
          {erreur === "npi" && <Alert tone="danger" title="Un NPI a treize chiffres." />}
          {erreur === "inconnu" && <Alert tone="attention" title="Aucun patient n’a ce NPI. Vérifiez-le avec le patient." />}
          {erreur === "service" && <Alert tone="danger" title="Le service soin ne répond pas. Réessayez dans un instant." />}
          <form action={rechercher} className="lf-formulaire">
            <ChampNpi />
            <Button type="submit" size="pro" icon="magnifying-glass">
              Ouvrir le patient
            </Button>
          </form>
          <p className="sn-meta">
            Le patient s’ouvre sur son identité, ses allergies et son groupe sanguin. Le dossier s’ouvre par une relation de
            soin : un cas que vous continuez ou que vous ouvrez.
          </p>
        </Card>
        <Card className="sn-panneau">
          <h2 className="sn-h3">Session</h2>
          <dl className="lf-etat">
            <dt>Connecté comme</dt>
            <dd>{session.role}</dd>
            <dt>Nom</dt>
            <dd>{session.nom}</dd>
            <dt>Établissement</dt>
            <dd>{session.nom_etablissement}</dd>
          </dl>
        </Card>
      </div>
    </Cadre>
  );
}
