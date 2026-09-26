import { OrdonnanceLine, StatusBadge } from "@lafia/design";
import { Illustration } from "@lafia/design/illustration";
import { connection } from "next/server";

import { Cadre, CarnetNonLu, Retour, Scene } from "../../composants/cadre";
import { doses, lire, quand, type LigneLue, type OrdonnanceLue } from "../../lib/carnet";

function detail(ligne: LigneLue): string | undefined {
  if (ligne.statut === "partiel" && ligne.quantite != null) {
    return `Remis : ${doses(ligne.remis, ligne.unite)} sur ${ligne.quantite}.`;
  }
  if (ligne.statut === "aretirer" && ligne.quantite != null) return `${doses(ligne.quantite, ligne.unite)} à retirer.`;
  return undefined;
}

function Ordonnance({ ordonnance, premiere }: { ordonnance: OrdonnanceLue; premiere: boolean }) {
  return (
    <section className="carnet-autres" aria-label={`Ordonnance ${ordonnance.numero}`}>
      <div className="carnet-ord-tete">
        <span className="carnet-doux">
          {`Ordonnance du ${quand(ordonnance.date, false)}${ordonnance.etablissement ? ` · ${ordonnance.etablissement}` : ""}`}
        </span>
        <span className="carnet-ord-numero">{ordonnance.numero}</span>
        <StatusBadge status={ordonnance.statut} />
        {premiere && <p className="carnet-grand">{ordonnance.message}</p>}
      </div>
      {premiere && ordonnance.statut === "aretirer" && (
        <div className="carnet-scene-illu">
          <Illustration name="citoyen-paye-pharmacie" decorative />
        </div>
      )}
      <div className="carnet-lignes">
        {ordonnance.lignes.map((ligne) => (
          <OrdonnanceLine
            key={ligne.id}
            status={ligne.statut}
            detail={detail(ligne)}
            posology={{ count: ligne.par_prise ?? undefined, moments: ligne.moments, days: ligne.jours ?? undefined }}
          >
            {ligne.produit}
          </OrdonnanceLine>
        ))}
      </div>
    </section>
  );
}

export default async function MesOrdonnances() {
  await connection();
  const lecture = await lire<OrdonnanceLue[]>("/ordonnances");
  if (lecture.etat !== "lu") {
    return (
      <Cadre connecte={lecture.etat !== "sans-session"}>
        <CarnetNonLu lecture={lecture} />
      </Cadre>
    );
  }
  const [courante, ...anciennes] = lecture.valeur;
  return (
    <Cadre>
      <Retour />
      <h1 className="carnet-titre">Mon ordonnance</h1>
      {courante ? (
        <>
          <Ordonnance ordonnance={courante} premiere />
          {anciennes.length > 0 && <h2 className="carnet-grand">Mes ordonnances précédentes</h2>}
          {anciennes.map((o) => (
            <Ordonnance key={o.numero} ordonnance={o} premiere={false} />
          ))}
        </>
      ) : (
        <Scene illustration="vide-ordonnance" titre="Aucune ordonnance pour le moment.">
          <p className="carnet-doux">Quand un soignant vous prescrit des médicaments, l'ordonnance apparaît ici.</p>
        </Scene>
      )}
    </Cadre>
  );
}
