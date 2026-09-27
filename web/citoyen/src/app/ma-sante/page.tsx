import { Alert, Icon, Posology, type NomIcone } from "@lafia/design";
import { connection } from "next/server";
import type { ReactNode } from "react";

import { Cadre, CarnetNonLu, Retour, Scene } from "../../composants/cadre";
import { lire, type MaSante } from "../../lib/carnet";

/** Une rubrique de « Ma santé » : une icône et un mot pour titre, puis ses éléments. */
function Rubrique({ icone, titre, children }: { icone: NomIcone; titre: string; children: ReactNode }) {
  return (
    <section className="carnet-rubrique" aria-label={titre}>
      <h2 className="carnet-rubrique-titre">
        <Icon name={icone} size={28} />
        <span>{titre}</span>
      </h2>
      <ul className="carnet-rubrique-liste">{children}</ul>
    </section>
  );
}

function depuis(valeur: string | null): string | null {
  if (!valeur) return null;
  return /^\d{4}$/.test(valeur) ? `Depuis ${valeur}` : valeur.charAt(0).toUpperCase() + valeur.slice(1);
}

function Sante({ sante }: { sante: MaSante }) {
  const vide =
    !sante.groupe_sanguin &&
    sante.allergies.length === 0 &&
    sante.antecedents.length === 0 &&
    sante.familiaux.length === 0 &&
    sante.traitements.length === 0;
  if (vide) {
    return (
      <Scene illustration="vide-consultations" titre="Rien n'est encore noté sur votre santé.">
        <p className="carnet-doux">
          Votre groupe sanguin, vos maladies passées et vos médicaments de tous les jours apparaîtront ici quand un soignant
          les notera.
        </p>
      </Scene>
    );
  }
  const medicaux = sante.antecedents.filter((a) => a.type === "medical");
  const chirurgicaux = sante.antecedents.filter((a) => a.type === "chirurgical");
  return (
    <>
      <section className="carnet-groupe" aria-label="Groupe sanguin">
        <Icon name="test-tube" size={36} />
        <span>
          Groupe sanguin
          <b>{sante.groupe_sanguin ?? "Pas encore connu"}</b>
        </span>
      </section>

      {sante.allergies.length > 0 && (
        <Alert tone="allergie" title={`Allergie : ${sante.allergies.join(", ")}`}>
          Dites-le à chaque soignant et au pharmacien.
        </Alert>
      )}

      {sante.traitements.length > 0 && (
        <Rubrique icone="pill" titre="Mes médicaments de tous les jours">
          {sante.traitements.map((t) => (
            <li key={t.libelle} className="carnet-element">
              <b className="carnet-element-nom">{t.libelle}</b>
              {t.moments.length > 0 && <Posology moments={t.moments} size={44} />}
              {t.posologie && <span>{t.posologie}</span>}
              {depuis(t.depuis) && <span className="carnet-doux">{depuis(t.depuis)}</span>}
            </li>
          ))}
        </Rubrique>
      )}

      {medicaux.length > 0 && (
        <Rubrique icone="stethoscope" titre="Mes maladies">
          {medicaux.map((a) => (
            <li key={a.libelle} className="carnet-element">
              <b className="carnet-element-nom">{a.libelle}</b>
              <span className="carnet-element-etat">
                <Icon name={a.actif ? "heartbeat" : "check"} size={20} />
                {a.actif ? "Toujours là" : "Guérie"}
              </span>
              {depuis(a.depuis) && <span className="carnet-doux">{depuis(a.depuis)}</span>}
            </li>
          ))}
        </Rubrique>
      )}

      {chirurgicaux.length > 0 && (
        <Rubrique icone="hospital" titre="Mes opérations">
          {chirurgicaux.map((a) => (
            <li key={a.libelle} className="carnet-element">
              <b className="carnet-element-nom">{a.libelle}</b>
              {a.depuis && <span className="carnet-doux">{/^\d{4}$/.test(a.depuis) ? `En ${a.depuis}` : a.depuis}</span>}
            </li>
          ))}
        </Rubrique>
      )}

      {sante.familiaux.length > 0 && (
        <Rubrique icone="users" titre="Dans ma famille">
          {sante.familiaux.map((f) => (
            <li key={`${f.lien}-${f.libelle}`} className="carnet-element">
              <b className="carnet-element-nom">{`${f.lien} : ${f.libelle.toLowerCase()}`}</b>
            </li>
          ))}
        </Rubrique>
      )}

      <p className="carnet-doux">Seul un soignant peut ajouter ou corriger ces informations. Parlez-lui si quelque chose manque.</p>
    </>
  );
}

export default async function MaSantePage() {
  await connection();
  const lecture = await lire<MaSante>("/ma-sante");
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
      <h1 className="carnet-titre">Ma santé</h1>
      <Sante sante={lecture.valeur} />
    </Cadre>
  );
}
