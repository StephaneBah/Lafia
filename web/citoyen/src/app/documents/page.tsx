import { Button, Icon } from "@lafia/design";
import { connection } from "next/server";

import { Cadre, CarnetNonLu, Retour, Scene } from "../../composants/cadre";
import { IconeDuDocument, PapierAbime, TexteRelu, pages } from "../../composants/documents";
import { OrigineEnMots } from "../../composants/origine";
import { lire, type DocumentLu, type MaTranscription } from "../../lib/carnet";

/** Le texte relu de chaque papier qui en a un ; un texte qui ne se lit pas cette fois ne bloque pas la liste. */
async function textesRelus(documents: DocumentLu[]): Promise<Record<string, MaTranscription>> {
  const lus = await Promise.all(
    documents
      .filter((d) => d.transcription)
      .map(async (d) => [d.id, await lire<MaTranscription>(`/documents/${encodeURIComponent(d.id)}/transcription`)] as const),
  );
  return Object.fromEntries(lus.flatMap(([id, l]) => (l.etat === "lu" ? [[id, l.valeur]] : [])));
}

/** Mes documents : mes anciens papiers, numérisés ; un toucher ouvre ses pages ; un papier relu se lit en texte. */
export default async function MesDocuments() {
  await connection();
  const lecture = await lire<DocumentLu[]>("/documents");
  if (lecture.etat !== "lu") {
    return (
      <Cadre connecte={lecture.etat !== "sans-session"}>
        <CarnetNonLu lecture={lecture} />
      </Cadre>
    );
  }
  const documents = lecture.valeur;
  const textes = await textesRelus(documents);
  return (
    <Cadre>
      <Retour />
      <h1 className="carnet-titre">Mes documents</h1>
      {documents.length === 0 ? (
        <Scene illustration="vide-consultations" titre="Aucun papier numérisé pour le moment.">
          <p className="carnet-doux">
            Vos anciens carnets, résultats et ordonnances apparaîtront ici quand ils auront été numérisés. Vous gardez vos papiers.
          </p>
        </Scene>
      ) : (
        <>
          <p className="carnet-doux">
            Vos anciens papiers, numérisés. Quand un papier a été relu, son texte recopié se lit en dessous.
          </p>
          <Button href="/par-etablissement" variant="secondary" icon="hospital" size="citizen" block>
            Voir par établissement
          </Button>
          <ul className="carnet-documents">
            {documents.map((d) => (
              <li key={d.id}>
                <a className="carnet-tuile" href={`/documents/${encodeURIComponent(d.id)}`}>
                  <span className="carnet-tuile-marque">
                    <IconeDuDocument type={d.type} />
                  </span>
                  <span>
                    {d.libelle}
                    <small>{[d.annee, pages(d.pages), d.etablissement].filter(Boolean).join(" · ")}</small>
                    <small>
                      <OrigineEnMots origine={d.origine} />
                    </small>
                    {d.lisibilite === "partiel" && (
                      <small className="carnet-document-etat">
                        <Icon name="warning" size={18} />
                        Difficile à lire
                      </small>
                    )}
                    <PapierAbime note={d.papier_abime} />
                    {textes[d.id] && (
                      <small className="carnet-document-etat carnet-relu">
                        <Icon name="check" size={18} />
                        Relu
                      </small>
                    )}
                  </span>
                  <Icon name="eye" size={24} label="Voir" />
                </a>
                {textes[d.id] && (
                  <details className="carnet-details-relu">
                    <summary>
                      <Icon name="list" size={22} />
                      Lire le texte relu
                    </summary>
                    <TexteRelu documentId={d.id} transcription={textes[d.id]} />
                  </details>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </Cadre>
  );
}
