import { Button, Icon } from "@lafia/design";
import { connection } from "next/server";

import { pluriel } from "../../../../libelles";
import { agentOuAccueil, Bureau } from "../../../Bureau";
import type { ParametresDuDepot } from "../depot";

function nombre(valeur: string | string[] | undefined): number {
  const lu = Number(typeof valeur === "string" ? valeur : NaN);
  return Number.isInteger(lu) && lu >= 0 ? lu : 0;
}

/** Le dépôt est clos : les papiers retournent au patient, Lafia garde les Documents. */
export default async function DepotClos({ searchParams }: ParametresDuDepot) {
  await connection();
  const agent = await agentOuAccueil();
  const parametres = await searchParams;
  const documents = nombre(parametres.documents);
  const pages = nombre(parametres.pages);

  return (
    <Bureau agent={agent} titre="Dépôt clos">
      <section className="num-carte num-clos" aria-labelledby="rendre">
        <span className="num-clos-marque" aria-hidden="true">
          <Icon name="check" size={40} />
        </span>
        <h2 className="num-clos-titre" id="rendre">
          Rendez ses papiers au patient
        </h2>
        <p className="num-clos-compte">
          {`${pluriel(documents, "document numérisé", "documents numérisés")}, ${pluriel(pages, "page")}, ajoutés à son dossier.`}
        </p>
        <p className="num-meta">
          Ils y portent la mention « numérisé, non vérifié » jusqu'à ce qu'un soignant les lise.
        </p>
        <div className="num-actions">
          <Button href="/" size="pro" icon="plus">
            Accueillir une autre personne
          </Button>
        </div>
      </section>
    </Bureau>
  );
}
