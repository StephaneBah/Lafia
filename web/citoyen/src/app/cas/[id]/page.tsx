import { StatusBadge, TimelineItem, type NomIcone } from "@lafia/design";
import { connection } from "next/server";

import { Cadre, CarnetNonLu, Retour, Scene } from "../../../composants/cadre";
import { lire, quand, type DetailDeCas, type VisiteLue } from "../../../lib/carnet";

function icone(visite: VisiteLue): NomIcone {
  if (visite.urgence) return "warning-octagon";
  if (visite.ordonnance) return "receipt";
  return "stethoscope";
}

export default async function UnCas({ params }: { params: Promise<{ id: string }> }) {
  await connection();
  const { id } = await params;
  const lecture = await lire<DetailDeCas>(`/cas/${encodeURIComponent(id)}`);
  if (lecture.etat !== "lu") {
    return (
      <Cadre connecte={lecture.etat !== "sans-session"}>
        <Retour href="/cas">Mes cas</Retour>
        <CarnetNonLu lecture={lecture} />
      </Cadre>
    );
  }
  const cas = lecture.valeur;
  const visites = cas.visites_lues;
  return (
    <Cadre>
      <Retour />
      <div className="carnet-cas-tete">
        <h1 className="carnet-titre">{cas.motif}</h1>
        <StatusBadge status={cas.en_cours ? "encours" : "termine"} />
      </div>
      <ol className="lf-timeline">
        {visites.map((visite, i) => (
          <TimelineItem
            key={visite.id}
            first={i === 0}
            last={!cas.en_cours && i === visites.length - 1}
            animate
            index={i}
            icon={icone(visite)}
            state={cas.en_cours && i === visites.length - 1 ? "current" : "done"}
            date={quand(visite.date)}
            place={[visite.etablissement, visite.soignant].filter(Boolean).join(" · ")}
            title={visite.motif ? `${visite.type} : ${visite.motif}` : visite.type}
          >
            <div className="carnet-visite-texte">
              {visite.mesures.length > 0 && (
                <ul className="carnet-mesures" aria-label="Mesures">
                  {visite.mesures.map((mesure) => (
                    <li key={mesure.libelle} className={mesure.alerte ? "is-alerte" : undefined}>
                      {`${mesure.libelle} : ${mesure.valeur}`}
                    </li>
                  ))}
                </ul>
              )}
              {visite.diagnostics.map((diagnostic) => (
                <span key={diagnostic} className="carnet-diagnostic">{diagnostic}</span>
              ))}
              {visite.ordonnance && (
                <a href="/ordonnance">{`Ordonnance ${visite.ordonnance}`}</a>
              )}
            </div>
          </TimelineItem>
        ))}
        {cas.en_cours && (
          <TimelineItem last animate index={visites.length} state="upcoming" title="Revenir si ça ne va pas mieux" />
        )}
      </ol>
      {!cas.en_cours && <Scene illustration="citoyen-cas-termine" titre={`Votre cas « ${cas.motif} » est terminé.`} />}
    </Cadre>
  );
}
