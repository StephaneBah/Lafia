import { Icon } from "@lafia/design";
import { RenduDeVolet } from "@lafia/commun/transcription";
import { connection } from "next/server";

import { Cadre, CarnetNonLu, Retour, Scene } from "../../composants/cadre";
import { MentionDuCarnet, adresseDeLaPage, voletDe } from "../../composants/documents";
import { lire, type EtablissementLu } from "../../lib/carnet";

/**
 * Par établissement : tout ce que mes anciens papiers relus racontent, regroupé par centre de santé ou
 * hôpital, dans l'ordre des dates. Rien n'est rangé ainsi au noyau : le service le calcule à chaque fois,
 * et un papier relu plus tard rejoint cette vue de lui-même.
 */
export default async function ParEtablissement() {
  await connection();
  const lecture = await lire<EtablissementLu[]>("/par-etablissement");
  if (lecture.etat !== "lu") {
    return (
      <Cadre connecte={lecture.etat !== "sans-session"}>
        <CarnetNonLu lecture={lecture} />
      </Cadre>
    );
  }
  const etablissements = lecture.valeur;
  return (
    <Cadre>
      <Retour href="/documents">Mes documents</Retour>
      <h1 className="carnet-titre">Par établissement</h1>
      {etablissements.length === 0 ? (
        <Scene illustration="vide-consultations" titre="Vos anciens papiers apparaîtront ici une fois relus.">
          <p className="carnet-doux">
            Des agents recopient vos papiers numérisés et les relisent. Ensuite, vous retrouverez ici ce qui s’est passé dans
            chaque centre de santé, dans l’ordre des dates.
          </p>
        </Scene>
      ) : (
        <>
          <MentionDuCarnet />
          <nav aria-label="Établissements" className="carnet-sommaire">
            <ul>
              {etablissements.map((e, i) => (
                <li key={e.etablissement}>
                  <a href={`#etablissement-${i}`} className="carnet-lien">
                    <Icon name="hospital" size={20} />
                    {`${e.etablissement} · ${e.volets.length}`}
                  </a>
                </li>
              ))}
            </ul>
          </nav>
          {etablissements.map((e, i) => (
            <section key={e.etablissement} id={`etablissement-${i}`} className="carnet-rubrique" aria-labelledby={`titre-${i}`}>
              <h2 id={`titre-${i}`} className="carnet-rubrique-titre">
                <Icon name="hospital" size={26} />
                {e.etablissement}
              </h2>
              <div className="lf-transcription">
                {e.volets.map((v, rang) => (
                  <RenduDeVolet
                    key={`${v.document_id}-${rang}`}
                    // L'établissement est déjà le titre de la rubrique : le volet ne le répète pas.
                    volet={voletDe(v, rang, null)}
                    urlDePage={(n) => adresseDeLaPage(v.document_id, n)}
                    entete={
                      <a href={`/documents/${encodeURIComponent(v.document_id)}`} className="carnet-lien carnet-voir-papier">
                        <Icon name="eye" size={20} />
                        Voir le papier
                      </a>
                    }
                  />
                ))}
              </div>
            </section>
          ))}
        </>
      )}
    </Cadre>
  );
}
