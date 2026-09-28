import { Alert, Button, Icon } from "@lafia/design";
import { connection } from "next/server";

import { Cadre, CarnetNonLu, Retour } from "../../../composants/cadre";
import { IconeDuDocument, PapierAbime, TexteRelu, pages } from "../../../composants/documents";
import { lire, type DocumentLu, type MaTranscription } from "../../../lib/carnet";

type Parametres = { params: Promise<{ id: string }> };

/** Un de mes documents : son texte relu s'il en a un, puis chaque page l'une sous l'autre ; un PDF s'ouvre
 * dans un nouvel onglet. */
export default async function MonDocument({ params }: Parametres) {
  await connection();
  const { id } = await params;
  const lecture = await lire<DocumentLu[]>("/documents");
  if (lecture.etat !== "lu") {
    return (
      <Cadre connecte={lecture.etat !== "sans-session"}>
        <CarnetNonLu lecture={lecture} />
      </Cadre>
    );
  }
  const document = lecture.valeur.find((d) => d.id === id);
  const texte = document?.transcription
    ? await lire<MaTranscription>(`/documents/${encodeURIComponent(document.id)}/transcription`)
    : null;
  return (
    <Cadre>
      <Retour href="/documents">Mes documents</Retour>
      {!document ? (
        <Alert tone="attention" title="Ce document n’est pas dans votre carnet." />
      ) : (
        <>
          <h1 className="carnet-titre carnet-titre-document">
            <IconeDuDocument type={document.type} size={44} />
            {document.libelle}
          </h1>
          <p className="carnet-doux">
            {[document.annee, pages(document.pages), document.etablissement].filter(Boolean).join(" · ")}
          </p>
          <PapierAbime note={document.papier_abime} />
          {texte?.etat === "lu" && (
            <section className="carnet-rubrique" aria-labelledby="texte-relu">
              <h2 id="texte-relu" className="carnet-rubrique-titre">
                <Icon name="list" size={26} />
                Le texte relu
              </h2>
              <TexteRelu documentId={document.id} transcription={texte.valeur} />
            </section>
          )}
          {texte?.etat === "lu" && (
            <h2 className="carnet-rubrique-titre">
              <Icon name="copy" size={26} />
              Les pages du papier
            </h2>
          )}
          <ol className="carnet-pages">
            {Array.from({ length: document.pages }, (_, i) => i + 1).map((n) => {
              const source = `/documents/${encodeURIComponent(document.id)}/pages/${n}`;
              return (
                <li key={n}>
                  {document.formats[n - 1] === "application/pdf" ? (
                    <Button href={source} target="_blank" rel="noopener" icon="arrow-square-out" size="citizen" block>
                      {`Ouvrir la page ${n}`}
                    </Button>
                  ) : (
                    <a href={source} target="_blank" rel="noopener" className="carnet-page">
                      {/* Les octets viennent de l'application, par la session du citoyen : pas d'optimisation d'image. */}
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={source} alt={`${document.libelle}, page ${n} sur ${document.pages}`} loading="lazy" />
                      <span className="carnet-doux">
                        <Icon name="eye" size={20} />
                        {`Page ${n}`}
                      </span>
                    </a>
                  )}
                </li>
              );
            })}
          </ol>
        </>
      )}
    </Cadre>
  );
}
