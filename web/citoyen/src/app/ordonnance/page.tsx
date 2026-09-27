import { Alert, Icon, Picto, Posology, StatusBadge } from "@lafia/design";
import { Illustration } from "@lafia/design/illustration";
import { connection } from "next/server";

import { Cadre, CarnetNonLu, Retour, Scene } from "../../composants/cadre";
import { doses, lire, nomCourt, quand, type LigneLue, type OrdonnanceLue } from "../../lib/carnet";

/** Ce qu'il reste à savoir de la quantité : combien en tout, combien remis. */
function quantite(ligne: LigneLue): string | null {
  if (ligne.quantite == null) return null;
  const tout = doses(ligne.quantite, ligne.unite);
  if (ligne.arret_allergie) return `${tout} prescrits, pas remis.`;
  if (ligne.statut === "partiel") return `${doses(ligne.remis, ligne.unite)} remis sur ${ligne.quantite}.`;
  if (ligne.statut === "aretirer") return `${tout} à retirer à la pharmacie.`;
  return `${tout} en tout.`;
}

/** Une ligne de l'ordonnance, aérée : le médicament en grand, son état, quand le prendre et combien. */
function Medicament({ ligne }: { ligne: LigneLue }) {
  const medicament = ligne.moments.length > 0 || ligne.jours != null;
  return (
    <li className="carnet-med">
      <span className="carnet-med-picto" aria-hidden="true">
        {medicament ? <Picto name="comprime" size={56} decorative /> : <Picto name="consultation" size={56} decorative />}
      </span>
      <div className="carnet-med-corps">
        <p className="carnet-med-nom">{ligne.produit}</p>
        {ligne.arret_allergie ? (
          <StatusBadge status="allergie" label="Pas remis : allergie" />
        ) : (
          <StatusBadge status={ligne.statut} />
        )}
        {ligne.moments.length > 0 && <Posology moments={ligne.moments} size={44} />}
        {medicament && (
          <p className="carnet-med-prise">
            {doses(ligne.par_prise, ligne.unite)}
            {ligne.moments.length > 1 ? " à chaque prise" : ""}
            {ligne.jours ? `, pendant ${ligne.jours} ${ligne.jours > 1 ? "jours" : "jour"}` : ""}
          </p>
        )}
        {quantite(ligne) && <p className="carnet-doux">{quantite(ligne)}</p>}
      </div>
    </li>
  );
}

function Entete({ ordonnance }: { ordonnance: OrdonnanceLue }) {
  return (
    <div className="carnet-ord-tete">
      <p className="carnet-ord-quand">
        <Icon name="calendar-blank" size={22} />
        <span>{`Ordonnance du ${quand(ordonnance.date, false)}`}</span>
      </p>
      {ordonnance.etablissement && (
        <p className="carnet-ord-quand">
          <Icon name="hospital" size={22} />
          <span>{ordonnance.etablissement}</span>
        </p>
      )}
      {ordonnance.prescripteur && (
        <p className="carnet-ord-quand">
          <Icon name="stethoscope" size={22} />
          <span>{ordonnance.prescripteur}</span>
        </p>
      )}
      <span className="carnet-ord-numero">{ordonnance.numero}</span>
    </div>
  );
}

function Lignes({ ordonnance }: { ordonnance: OrdonnanceLue }) {
  const arretees = ordonnance.lignes.filter((ligne) => ligne.arret_allergie);
  return (
    <>
      <ul className="carnet-meds" aria-label="Médicaments et soins prescrits">
        {ordonnance.lignes.map((ligne) => (
          <Medicament key={ligne.id} ligne={ligne} />
        ))}
      </ul>
      {arretees.map((ligne) => (
        <Alert key={ligne.id} tone="info" title={`${nomCourt(ligne.produit)} : pas remis`}>
          Le pharmacien l'a retiré à cause de votre allergie déclarée. Rien à faire de votre côté.
        </Alert>
      ))}
    </>
  );
}

function OrdonnanceCourante({ ordonnance }: { ordonnance: OrdonnanceLue }) {
  return (
    <section className="carnet-ord" aria-label={`Ordonnance ${ordonnance.numero}`}>
      <Entete ordonnance={ordonnance} />
      <div className="carnet-ord-etat">
        <StatusBadge status={ordonnance.statut} size="large" />
        <p className="carnet-grand">{ordonnance.message}</p>
      </div>
      {ordonnance.statut === "aretirer" && (
        <div className="carnet-scene-illu">
          <Illustration name="citoyen-paye-pharmacie" decorative />
        </div>
      )}
      <Lignes ordonnance={ordonnance} />
    </section>
  );
}

/** Une ancienne ordonnance : une ligne fermée, sa date et son état ; ouverte, tout son détail. */
function OrdonnanceAncienne({ ordonnance }: { ordonnance: OrdonnanceLue }) {
  return (
    <details className="carnet-ancienne">
      <summary>
        <Icon name="receipt" size={28} />
        <span className="carnet-ancienne-titre">
          {quand(ordonnance.date, false)}
          <small>{`${ordonnance.lignes.length} ${ordonnance.lignes.length > 1 ? "lignes" : "ligne"}${ordonnance.etablissement ? ` · ${ordonnance.etablissement}` : ""}`}</small>
        </span>
        <StatusBadge status={ordonnance.statut} size="pro" />
        <Icon name="caret-down" size={22} className="carnet-ancienne-fleche" />
      </summary>
      <div className="carnet-ancienne-corps">
        <Entete ordonnance={ordonnance} />
        <Lignes ordonnance={ordonnance} />
      </div>
    </details>
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
          <OrdonnanceCourante ordonnance={courante} />
          {anciennes.length > 0 && (
            <section className="carnet-anciennes" aria-labelledby="anciennes-ordonnances">
              <h2 id="anciennes-ordonnances" className="carnet-grand">
                Anciennes ordonnances
              </h2>
              {anciennes.map((o) => (
                <OrdonnanceAncienne key={o.numero} ordonnance={o} />
              ))}
            </section>
          )}
        </>
      ) : (
        <Scene illustration="vide-ordonnance" titre="Aucune ordonnance pour le moment.">
          <p className="carnet-doux">Quand un soignant vous prescrit des médicaments, l'ordonnance apparaît ici.</p>
        </Scene>
      )}
    </Cadre>
  );
}
