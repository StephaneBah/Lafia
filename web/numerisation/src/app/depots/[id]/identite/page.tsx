import { Button, Icon } from "@lafia/design";
import { connection } from "next/server";

import { abandonnerLeDepot } from "../../../actions";
import { agentOuAccueil, Bureau } from "../../../Bureau";
import { depotOuRefus, type ParametresDuDepot } from "../depot";

/**
 * Étape 2 : qui le NPI désigne, écrit en grand, à comparer avec la pièce présentée. Le NPI n'est pas
 * répété : l'agent vient de le taper, et il ne voyage que dans le corps des requêtes.
 */
export default async function ConfirmerLIdentite({ params }: ParametresDuDepot) {
  await connection();
  const agent = await agentOuAccueil();
  const { id } = await params;
  const chemin = `/depots/${encodeURIComponent(id)}`;
  const lu = await depotOuRefus(id, `${chemin}/identite`);

  return (
    <Bureau agent={agent} etape={2} titre="Confirmer l'identité">
      {"refus" in lu ? (
        lu.refus
      ) : (
        <section className="num-carte num-identite" aria-labelledby="comparer">
          <p className="num-consigne" id="comparer">
            <Icon name="identification-card" size={28} />
            <span>Comparez avec la pièce présentée</span>
          </p>
          <dl className="num-personne">
            <dt>Nom</dt>
            <dd>{lu.depot.patient.nom}</dd>
            <dt>Prénoms</dt>
            <dd>{lu.depot.patient.prenoms}</dd>
            <dt>Année de naissance</dt>
            <dd className="num-chiffres">{lu.depot.patient.annee_de_naissance}</dd>
          </dl>
          <div className="num-actions">
            <Button href={`${chemin}/numeriser`} size="pro" icon="check">
              Continuer
            </Button>
            <form action={abandonnerLeDepot}>
              <input type="hidden" name="depot" value={id} />
              <Button type="submit" size="pro" variant="secondary" icon="arrow-left">
                Ce n'est pas la bonne personne
              </Button>
            </form>
          </div>
        </section>
      )}
    </Bureau>
  );
}
