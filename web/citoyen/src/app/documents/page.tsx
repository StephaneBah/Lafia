import { Icon } from "@lafia/design";
import { connection } from "next/server";

import { Cadre, CarnetNonLu, Retour, Scene } from "../../composants/cadre";
import { IconeDuDocument, pages } from "../../composants/documents";
import { OrigineEnMots } from "../../composants/origine";
import { lire, type DocumentLu } from "../../lib/carnet";

/** Mes documents : mes anciens papiers, numérisés ; un toucher ouvre ses pages. */
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
          <p className="carnet-doux">Vos anciens papiers, numérisés. Personne ne les a encore vérifiés.</p>
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
                  </span>
                  <Icon name="eye" size={24} label="Voir" />
                </a>
              </li>
            ))}
          </ul>
        </>
      )}
    </Cadre>
  );
}
