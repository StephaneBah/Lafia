import { Icon, Picto, type NomIcone } from "@lafia/design";
import { Illustration } from "@lafia/design/illustration";
import { connection } from "next/server";

import { Cadre, CarnetNonLu, Retour } from "../../composants/cadre";
import { lire, quand, type AccesLu } from "../../lib/carnet";

const ICONES_DES_SERVICES: Record<string, NomIcone> = {
  soin: "stethoscope",
  caisse: "cash-register",
  pharmacie: "pill",
  citoyen: "user",
  numerisation: "copy",
};

function Ligne({ acces }: { acces: AccesLu }) {
  return (
    <li className={acces.urgence ? "carnet-acces is-urgence" : "carnet-acces"}>
      {acces.urgence ? (
        <Picto name="urgence" size={36} decorative />
      ) : (
        <Icon name={acces.depot ? "copy" : (ICONES_DES_SERVICES[acces.service ?? ""] ?? "eye")} size={32} />
      )}
      <div>
        <b>{acces.etablissement && !acces.vous ? `${acces.qui} · ${acces.etablissement}` : acces.qui}</b>
        {acces.motif}
        {acces.depot && (
          <div>
            <a href="/documents" className="carnet-lien">
              Voir mes documents
            </a>
          </div>
        )}
        {acces.raison && <div className="carnet-raison">{`Motif : ${acces.raison}`}</div>}
        <div className="carnet-quand">{quand(acces.date)}</div>
      </div>
    </li>
  );
}

export default async function QuiAOuvertMonDossier() {
  await connection();
  const lecture = await lire<AccesLu[]>("/acces");
  if (lecture.etat !== "lu") {
    return (
      <Cadre connecte={lecture.etat !== "sans-session"}>
        <CarnetNonLu lecture={lecture} />
      </Cadre>
    );
  }
  const journal = lecture.valeur;
  const urgence = journal.find((a) => a.urgence);
  return (
    <Cadre>
      <Retour />
      <h1 className="carnet-titre">Qui a ouvert mon dossier</h1>
      <p className="carnet-doux">Chaque ouverture de votre dossier est notée : qui, où, quand et pourquoi.</p>
      {urgence && (
        <div className="carnet-scene-illu">
          <Illustration name="citoyen-urgence-tracee" label="Un accès d'urgence à votre dossier a été noté, avec son motif." />
        </div>
      )}
      <ul className="carnet-journal">
        {journal.map((acces, i) => (
          <Ligne key={`${acces.date}-${i}`} acces={acces} />
        ))}
      </ul>
    </Cadre>
  );
}
