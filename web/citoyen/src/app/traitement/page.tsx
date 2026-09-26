import { Picto } from "@lafia/design";
import { connection } from "next/server";

import { Cadre, CarnetNonLu, Retour, Scene } from "../../composants/cadre";
import { LIBELLES_DES_MOMENTS, MOMENTS, doses, lire, nomCourt, type Moment, type Prise, type TraitementDuJour } from "../../lib/carnet";

/** Autant de comprimés dessinés que de comprimés à prendre ; un demi dessiné en demi. */
function Comprimes({ prise }: { prise: Prise }) {
  const nombre = prise.par_prise ?? 1;
  const entiers = Math.floor(nombre);
  return (
    <span className="carnet-dose" aria-hidden="true">
      {Array.from({ length: Math.min(entiers, 8) }, (_, i) => (
        <Picto key={i} name="comprime" size={30} decorative />
      ))}
      {nombre % 1 !== 0 && <Picto name="comprime-demi" size={30} decorative />}
    </span>
  );
}

function MomentDuJour({ moment, prises, prochain }: { moment: Moment; prises: Prise[]; prochain: boolean }) {
  const classes = ["carnet-moment", prises.length ? "" : "is-vide", prochain ? "is-prochain" : ""].filter(Boolean).join(" ");
  return (
    <section className={classes} aria-label={LIBELLES_DES_MOMENTS[moment]} aria-current={prochain ? "time" : undefined}>
      <div className="carnet-moment-nom">
        <Picto name={moment} size={48} decorative />
        <span>{LIBELLES_DES_MOMENTS[moment]}</span>
      </div>
      {prises.length ? (
        <ul className="carnet-doses" role="list" style={{ listStyle: "none", margin: 0, padding: 0 }}>
          {prises.map((prise) => (
            <li key={prise.produit} className="carnet-dose">
              <span className="carnet-dose-nom">{nomCourt(prise.produit)}</span>
              <Comprimes prise={prise} />
              <span className="carnet-dose-mots">{`${doses(prise.par_prise, prise.unite)} · jour ${prise.jour} sur ${prise.jours}`}</span>
            </li>
          ))}
        </ul>
      ) : (
        <span className="carnet-doux">Rien à prendre</span>
      )}
    </section>
  );
}

export default async function MonTraitement() {
  await connection();
  const lecture = await lire<TraitementDuJour>("/traitement");
  if (lecture.etat !== "lu") {
    return (
      <Cadre connecte={lecture.etat !== "sans-session"}>
        <CarnetNonLu lecture={lecture} />
      </Cadre>
    );
  }
  const traitement = lecture.valeur;
  const rien = MOMENTS.every((m) => traitement.moments[m].length === 0);
  return (
    <Cadre>
      <Retour />
      <h1 className="carnet-titre">Mon traitement</h1>
      {rien ? (
        <Scene illustration="vide-traitement" titre="Rien à prendre aujourd'hui.">
          <p className="carnet-doux">Quand un soignant vous prescrit un traitement, il apparaît ici en images.</p>
        </Scene>
      ) : (
        <>
          <p className="carnet-doux">Aujourd'hui, à chaque moment de la journée :</p>
          <div className="carnet-soleil" data-moment={traitement.prochain ?? "nuit"} aria-hidden="true">
            <svg viewBox="0 0 40 40">
              <circle cx="20" cy="20" r="11" fill="#F2B544" stroke="#121212" strokeWidth="3" />
            </svg>
          </div>
          {MOMENTS.map((moment) => (
            <MomentDuJour key={moment} moment={moment} prises={traitement.moments[moment]} prochain={moment === traitement.prochain} />
          ))}
        </>
      )}
    </Cadre>
  );
}
