import { EtatDeLActeur } from "@lafia/commun";
import { Alert } from "@lafia/design";
import { connection } from "next/server";

import { ACTEUR, TITRE } from "../libelles";
import { lireAgent } from "../numerisation";
import { Accueillir } from "./Accueillir";
import { Bureau } from "./Bureau";

type Parametres = { searchParams: Promise<Record<string, string | string[] | undefined>> };

/**
 * L'accueil du bureau de numérisation. Sans session : l'état du service et « Se connecter ». Avec :
 * la première étape d'un dépôt, accueillir la personne et ses papiers.
 */
export default async function Accueil({ searchParams }: Parametres) {
  await connection();
  const agent = await lireAgent();
  if (!agent) return <EtatDeLActeur titre={TITRE} service={ACTEUR} avecConnexion />;
  const { annule } = await searchParams;

  return (
    <Bureau agent={agent} etape={1} titre="Accueillir une personne">
      {annule && (
        <Alert tone="info" title="Dépôt annulé : rien n'a été ajouté au dossier.">
          Vérifiez le NPI avec la personne, puis ouvrez un nouveau dépôt.
        </Alert>
      )}
      <Accueillir />
    </Bureau>
  );
}
