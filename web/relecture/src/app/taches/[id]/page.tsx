import { MENTION_PATRIMONIALE, RenduDeTranscription, lireTranscription } from "@lafia/commun/transcription";
import { Alert, Button, formatDate, Icon } from "@lafia/design";
import { redirect } from "next/navigation";
import { connection } from "next/server";

import { adresseDeLaPage, descriptionDuDocument, iconeDuType, libelleDuDocument, pluriel } from "../../../libelles";
import { estSoignant, lireTache, type TacheDetaillee } from "../../../relecture";
import { Bureau, Refus, relecteurOuAccueil } from "../../Bureau";
import { EtatDeTache } from "../../EtatDeTache";
import { Atelier } from "./Atelier";
import { Contexte } from "./Contexte";
import { Controler } from "./Controler";
import { Feuilles } from "./Feuilles";
import { Valider } from "./Valider";

type Parametres = {
  params: Promise<{ id: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

const TITRES = {
  relecture: "Relire un document",
  controle: "Contrôler une transcription",
  validation: "Valider une extraction",
} as const;

const FAITS: Record<string, string> = {
  confirmee: "Transcription confirmée : elle part au Contrôle.",
  close: "Relecture close sans Transcription.",
  acceptee: "Transcription acceptée : elle est relue.",
  renvoyee: "Transcription renvoyée à son relecteur.",
  validation: "Validation enregistrée.",
};

/** Ce que l'agent de numérisation a déclaré du Document, et l'échéance de la tâche. */
function Declare({ tache }: { tache: TacheDetaillee }) {
  const { document } = tache;
  return (
    <dl className="rel-declare">
      <dt>Document</dt>
      <dd className="rel-declare-type">
        <Icon name={iconeDuType(document.type)} size={20} />
        <span>{libelleDuDocument(document)}</span>
      </dd>
      <dt>Année déclarée</dt>
      <dd className="rel-chiffres">{document.annee ?? "inconnue"}</dd>
      <dt>Pages</dt>
      <dd>{pluriel(document.pages, "page")}</dd>
      {tache.echeance && (
        <>
          <dt>À rendre avant le</dt>
          <dd>{formatDate(tache.echeance)}</dd>
        </>
      )}
    </dl>
  );
}

/**
 * Une tâche : ses pages à gauche, et à droite, selon l'étape, la Transcription à relire, à contrôler, ou
 * les propositions de l'Extraction à valider. Aucune identité de patient n'arrive jusqu'ici.
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
        <Refus statut={lue.statut === 409 ? 404 : lue.statut} ici={ici} />
      </Bureau>
    );
  }
  const tache = lue.corps;
  const description = descriptionDuDocument(tache.document);

  // Une étape que ce rôle ne fait pas : Relecture et Contrôle aux agents de relecture, validation aux soignants.
  if ((tache.etape === "validation") !== estSoignant(relecteur)) {
    return (
      <Bureau relecteur={relecteur} titre="Tâche de relecture" retour>
        <Refus statut={403} ici={ici} />
      </Bureau>
    );
  }

  const titre = TITRES[tache.etape];
  const precedente = typeof fait === "string" && FAITS[fait];

  if (tache.statut === "terminee") {
    return (
      <Bureau relecteur={relecteur} titre={titre} retour>
        <Alert
          tone="succes"
          title="Cette tâche est faite."
          actions={
            <Button href="/" size="pro" icon="list">
              Revenir à ma semaine
            </Button>
          }
        >
          Une tâche faite ne se refait pas ici. Si vous pensez vous être trompé, signalez-le à votre responsable.
        </Alert>
      </Bureau>
    );
  }

  return (
    <Bureau relecteur={relecteur} titre={titre} retour large>
      {precedente && (
        <Alert tone="succes" title={precedente}>
          Voici la tâche suivante.
        </Alert>
      )}

      <div className="rel-tache-meta">
        <EtatDeTache tache={tache} />
        <Declare tache={tache} />
      </div>

      {tache.etape === "relecture" &&
        (tache.markdown === null ? (
          <Alert tone="attention" title="La machine n'a pas encore lu ce Document.">
            Rechargez la page dans un instant : la lecture se fait à la première ouverture.
          </Alert>
        ) : (
          <Atelier
            tache={tache.id}
            document={tache.document}
            description={description}
            markdown={tache.markdown}
            version={tache.version}
            modele={tache.modele}
            texte={tache.texte}
            notes={tache.notes_de_controle}
            renvoyee={tache.renvoyee}
          />
        ))}

      {tache.etape === "controle" && (
        <Controler
          tache={tache.id}
          document={tache.document}
          description={description}
          markdown={tache.markdown ?? ""}
          resume={tache.resume}
          modele={tache.modele}
          texte={tache.texte}
        />
      )}

      {tache.etape === "validation" && (
        <div className="rel-atelier">
          <Feuilles tache={tache.id} pages={tache.document.pages} formats={tache.document.formats} description={description} />
          <section className="rel-panneau" aria-labelledby="propositions">
            <Contexte modele={tache.modele} notes={[]} texte={tache.texte} consigne="validation" />
            {tache.markdown && (
              <details className="rel-texte rel-transcription-relue">
                <summary>La Transcription relue de ce Document</summary>
                <p className="lf-mention-patrimoniale">
                  <Icon name="info" size={20} />
                  <span>{MENTION_PATRIMONIALE}</span>
                </p>
                <RenduDeTranscription
                  transcription={lireTranscription(tache.markdown, tache.document.pages)}
                  urlDePage={(n) => adresseDeLaPage(tache.id, n)}
                />
              </details>
            )}
            <h2 className="lf-app-sous-titre-fort" id="propositions">
              Ce que la machine propose
            </h2>
            <p className="rel-meta">
              {tache.modele ? `Lu par le modèle ${tache.modele.nom}, version ${tache.modele.version}. ` : ""}
              Seul ce que vous acceptez ou corrigez entre dans le dossier, avec l'origine « extraction ».
            </p>
            <Valider tache={tache.id} propositions={tache.propositions ?? []} />
          </section>
        </div>
      )}
    </Bureau>
  );
}
