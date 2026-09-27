import { Alert, Button, Icon } from "@lafia/design";
import { redirect } from "next/navigation";
import { connection } from "next/server";

import {
  estDeDemonstration,
  iconeDuType,
  libelleDeLisibilite,
  libelleDuType,
  libelleDuVerdict,
  pluriel,
} from "../../../libelles";
import { estSoignant, lireTache, type TacheDetaillee } from "../../../relecture";
import { Bureau, Refus, relecteurOuAccueil } from "../../Bureau";
import { EtatDeTache } from "../../EtatDeTache";
import { Pages } from "./Pages";
import { Trier } from "./Trier";
import { Valider } from "./Valider";

type Parametres = {
  params: Promise<{ id: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

/** Ce que l'agent de numérisation a déclaré du Document : son type, son année, ses pages. */
function Declare({ tache }: { tache: TacheDetaillee }) {
  const { document } = tache;
  const lisibilite = libelleDeLisibilite(document.lisibilite);
  return (
    <dl className="rel-declare">
      <dt>Type déclaré</dt>
      <dd className="rel-declare-type">
        <Icon name={iconeDuType(document.type)} size={20} />
        <span>{libelleDuType(document.type)}</span>
      </dd>
      <dt>Année déclarée</dt>
      <dd className="rel-chiffres">{document.annee}</dd>
      <dt>Pages</dt>
      <dd>{pluriel(document.pages, "page")}</dd>
      {lisibilite && (
        <>
          <dt>Lisibilité notée au dépôt</dt>
          <dd>{lisibilite}</dd>
        </>
      )}
    </dl>
  );
}

/** Le rappel du pseudonymat : le système ne dit pas qui est le patient ; une page, parfois, si. */
function Pseudonymat() {
  return (
    <p className="rel-pseudonymat">
      <Icon name="shield-check" size={22} />
      <span>Vous ne voyez pas qui est le patient. Si la page montre un nom, n'en faites rien.</span>
    </p>
  );
}

/**
 * Une tâche de relecture : ses pages en grand, et à côté, selon l'étape, le verdict du triage ou les
 * propositions de l'Extraction à valider. Aucune identité de patient n'arrive jusqu'ici.
 */
export default async function LaTache({ params, searchParams }: Parametres) {
  await connection();
  const relecteur = await relecteurOuAccueil();
  const { id } = await params;
  const { fait } = await searchParams;
  const ici = `/taches/${encodeURIComponent(id)}`;

  const lue = await lireTache(id);
  if (!lue.ok) {
    if (lue.statut === 401) redirect("/connexion");
    return (
      <Bureau relecteur={relecteur} titre="Tâche de relecture" retour>
        <Refus statut={lue.statut} ici={ici} />
      </Bureau>
    );
  }
  const tache = lue.corps;
  const triage = tache.etape === "triage";
  const description = `${libelleDuType(tache.document.type)}, ${tache.document.annee}`;

  // Une étape que ce rôle ne fait pas : le triage aux agents de relecture, la validation aux soignants.
  if (triage === estSoignant(relecteur)) {
    return (
      <Bureau relecteur={relecteur} titre="Tâche de relecture" retour>
        <Refus statut={403} ici={ici} />
      </Bureau>
    );
  }

  const titre = triage ? "Trier un document" : "Valider une extraction";

  if (tache.verdict) {
    return (
      <Bureau relecteur={relecteur} titre={titre} retour>
        <Alert
          tone="succes"
          title={triage ? `Cette tâche est triée : ${libelleDuVerdict(tache.verdict)}.` : "Cette extraction est validée."}
          actions={
            <Button href="/" size="pro" icon="list">
              Revenir à ma semaine
            </Button>
          }
        >
          Une tâche faite ne se refait pas. Si vous pensez vous être trompé, signalez-le à votre responsable.
        </Alert>
      </Bureau>
    );
  }

  return (
    <Bureau relecteur={relecteur} titre={titre} retour large>
      {fait && (
        <Alert tone="succes" title="Tâche précédente enregistrée.">
          Voici la suivante.
        </Alert>
      )}
      {!triage && estDeDemonstration(tache.modele) && (
        <Alert tone="attention" title={`Extraction de démonstration — modèle ${tache.modele!.nom} ${tache.modele!.version}`}>
          Ces propositions ne viennent pas d'une vraie lecture de la page : elles servent à montrer le travail. Comparez
          chacune avec la page avant de l'accepter.
        </Alert>
      )}

      <div className="rel-tache-meta">
        <EtatDeTache tache={tache} />
        <Declare tache={tache} />
      </div>

      <div className={triage ? "rel-plan rel-plan--triage" : "rel-plan rel-plan--validation"}>
        <Pages tache={tache.id} pages={tache.document.pages} description={description} />

        <div className="rel-cote">
          <Pseudonymat />
          {triage ? (
            <section className="rel-carte" aria-labelledby="verdict">
              <h2 className="lf-app-sous-titre-fort" id="verdict">
                Votre verdict
              </h2>
              <Trier tache={tache.id} typeDeclare={tache.document.type} anneeDeclaree={String(tache.document.annee)} />
            </section>
          ) : (
            <section className="rel-carte" aria-labelledby="propositions">
              <h2 className="lf-app-sous-titre-fort" id="propositions">
                Ce que la machine propose
              </h2>
              <p className="rel-meta">
                {tache.modele
                  ? `Lu par le modèle ${tache.modele.nom}, version ${tache.modele.version}. `
                  : ""}
                Seul ce que vous acceptez ou corrigez entre dans le dossier, avec l'origine « extraction ».
              </p>
              {tache.texte && (
                <details className="rel-texte">
                  <summary>Texte lu par la machine</summary>
                  <pre>{tache.texte}</pre>
                </details>
              )}
              <Valider tache={tache.id} propositions={tache.propositions ?? []} />
            </section>
          )}
        </div>
      </div>
    </Bureau>
  );
}
