import { Alert, Button, Icon } from "@lafia/design";
import { connection } from "next/server";

import { adresseDuDepot, iconeDuType, libelleDuType, pluriel } from "../../../libelles";
import { abandonnerLeDepot, cloreLeDepot } from "../../actions";
import { agentOuAccueil, Bureau } from "../../Bureau";
import { depotOuRefus, DepotClos, type ParametresDuDepot } from "./depot";
import { Vignette } from "./Vignette";

/**
 * Étape 4 : les Documents numérisés dans ce dépôt, chacun avec sa première page, servie par le
 * service numerisation. Puis un autre document, ou la clôture.
 */
export default async function LeDepot({ params, searchParams }: ParametresDuDepot) {
  await connection();
  const agent = await agentOuAccueil();
  const { id } = await params;
  const { erreur } = await searchParams;
  const chemin = `/depots/${encodeURIComponent(id)}`;
  if (erreur === "clos") {
    return (
      <Bureau agent={agent} etape={4} titre="Le dépôt">
        <DepotClos />
      </Bureau>
    );
  }
  const lu = await depotOuRefus(id, chemin);
  if ("refus" in lu) {
    return (
      <Bureau agent={agent} etape={4} titre="Le dépôt">
        {lu.refus}
      </Bureau>
    );
  }

  const { patient, documents } = lu.depot;
  const pages = documents.reduce((total, document) => total + document.pages, 0);

  return (
    <Bureau agent={agent} etape={4} titre="Le dépôt">
      {erreur === "service" && (
        <Alert tone="danger" title="Le service numérisation ne répond pas : le dépôt n'est pas clos.">
          Réessayez de le clore dans un instant. Gardez les papiers jusque-là.
        </Alert>
      )}
      <section className="num-carte num-depot" aria-labelledby="documents-numerises">
        <div className="num-depot-tete">
          <h2 className="lf-app-sous-titre-fort" id="documents-numerises">
            Documents numérisés
          </h2>
          <p className="num-meta">
            {`${patient.prenoms} ${patient.nom} · ${pluriel(documents.length, "document")} · ${pluriel(pages, "page")}`}
          </p>
        </div>
        {documents.length === 0 ? (
          <p className="num-vide">Aucun document numérisé dans ce dépôt pour l'instant.</p>
        ) : (
          <ul className="num-documents">
            {documents.map((document) => (
              <li key={document.id} className="num-document">
                {/* La première page, servie par le service, du même domaine : le cookie de session l'accompagne. */}
                <Vignette
                  src={`${adresseDuDepot(id)}/documents/${encodeURIComponent(document.id)}/pages/1`}
                  alt={`Première page : ${libelleDuType(document.type)}, ${document.annee}`}
                />
                <div className="num-document-texte">
                  <p className="num-document-type">
                    <Icon name={iconeDuType(document.type)} size={20} />
                    <span>{libelleDuType(document.type)}</span>
                  </p>
                  <p className="num-meta">{`${document.annee} · ${pluriel(document.pages, "page")}`}</p>
                </div>
              </li>
            ))}
          </ul>
        )}
        <div className="num-actions">
          <Button href={`${chemin}/numeriser`} size="pro" icon="plus" variant={documents.length ? "secondary" : "primary"}>
            {documents.length ? "Numériser un autre document" : "Numériser un document"}
          </Button>
          {documents.length > 0 ? (
            <form action={cloreLeDepot}>
              <input type="hidden" name="depot" value={id} />
              <Button type="submit" size="pro" icon="check">
                Clore le dépôt
              </Button>
            </form>
          ) : (
            // Un dépôt vide n'écrit rien au dossier : l'annuler le ferme, simplement.
            <form action={abandonnerLeDepot}>
              <input type="hidden" name="depot" value={id} />
              <Button type="submit" size="pro" variant="ghost" icon="x">
                Annuler le dépôt
              </Button>
            </form>
          )}
        </div>
      </section>
    </Bureau>
  );
}
