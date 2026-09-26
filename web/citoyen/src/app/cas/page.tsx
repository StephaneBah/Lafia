import { Icon, StatusBadge } from "@lafia/design";
import { connection } from "next/server";

import { Cadre, CarnetNonLu, Retour, Scene } from "../../composants/cadre";
import { lire, quand, type ResumeDeCas } from "../../lib/carnet";

export default async function MesCas() {
  await connection();
  const lecture = await lire<ResumeDeCas[]>("/cas");
  if (lecture.etat !== "lu") {
    return (
      <Cadre connecte={lecture.etat !== "sans-session"}>
        <CarnetNonLu lecture={lecture} />
      </Cadre>
    );
  }
  return (
    <Cadre>
      <Retour />
      <h1 className="carnet-titre">Mes cas de visite</h1>
      {lecture.valeur.length === 0 ? (
        <Scene illustration="vide-cas" titre="Aucun cas pour le moment.">
          <p className="carnet-doux">Chaque problème de santé soigné dans un centre apparaîtra ici, visite après visite.</p>
        </Scene>
      ) : (
        <nav className="carnet-tuiles" aria-label="Mes cas de visite">
          {lecture.valeur.map((cas) => (
            <a key={cas.id} className="carnet-tuile" href={`/cas/${encodeURIComponent(cas.id)}`}>
              <span className="carnet-tuile-marque">
                <Icon name={cas.en_cours ? "heartbeat" : "check"} size={36} />
              </span>
              <span>
                {cas.motif}
                <small>{`${quand(cas.debut, false)}${cas.etablissement ? ` · ${cas.etablissement}` : ""}`}</small>
                <StatusBadge status={cas.en_cours ? "encours" : "termine"} size="pro" />
              </span>
              <Icon name="arrow-left" size={22} className="carnet-aller" />
            </a>
          ))}
        </nav>
      )}
    </Cadre>
  );
}
