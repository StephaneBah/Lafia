import { EtatDeLActeur } from "@lafia/commun";
import { Alert, Button, formatDate, Icon } from "@lafia/design";
import { redirect } from "next/navigation";
import { connection } from "next/server";

import {
  ACTEUR,
  descriptionDuDocument,
  iconeDuType,
  LIBELLES_DES_ETAPES,
  libelleDeLIssue,
  libelleDuDocument,
  pluriel,
  TITRE,
} from "../libelles";
import { estFaite, estSoignant, lireMaSemaine, lireRelecteur, lireSuivi, type Suivi, type Tache } from "../relecture";
import type { Etape } from "../types";
import { Bureau, Refus } from "./Bureau";
import { EtatDeTache } from "./EtatDeTache";

type Parametres = { searchParams: Promise<Record<string, string | string[] | undefined>> };

const FAITS: Record<string, string> = {
  confirmee: "Transcription confirmée : elle part au Contrôle d'un autre agent de relecture.",
  close: "Relecture close sans Transcription.",
  acceptee: "Transcription acceptée : elle est relue.",
  renvoyee: "Transcription renvoyée à son relecteur, avec votre note.",
  validation: "Validation enregistrée.",
};

/** L'échéance de la semaine : la plus proche des tâches qui restent, sinon la dernière. */
function echeanceDeLaSemaine(taches: Tache[]): string | null {
  const restantes = taches.filter((tache) => !estFaite(tache)).map((tache) => tache.echeance);
  const dates = (restantes.length ? restantes : taches.map((tache) => tache.echeance)).filter((d): d is string => Boolean(d)).sort();
  return dates[0] ?? null;
}

/** Où l'on en est : un compte écrit en toutes lettres, et une barre qui le redit. */
function Avancement({ faites, total, echeance }: { faites: number; total: number; echeance: string | null }) {
  const pourcent = total ? Math.round((faites / total) * 100) : 0;
  return (
    <div className="rel-avancement">
      <p className="rel-avancement-compte">
        <span className="rel-chiffres">{`${faites} / ${total}`}</span>
        <span>{` ${total > 1 ? "tâches faites" : "tâche faite"}`}</span>
      </p>
      <div
        className="rel-barre"
        role="progressbar"
        aria-label="Tâches faites cette semaine"
        aria-valuemin={0}
        aria-valuemax={total}
        aria-valuenow={faites}
        aria-valuetext={`${faites} sur ${total}`}
      >
        <span className="rel-barre-plein" style={{ width: `${pourcent}%` }} />
      </div>
      {echeance && (
        <p className="rel-meta rel-echeance">
          <Icon name="calendar-blank" size={20} />
          <span>{`À rendre avant le ${formatDate(echeance)}`}</span>
        </p>
      )}
    </div>
  );
}

const ORDRE_DES_ETAPES: Etape[] = ["relecture", "controle", "validation"];

const CONSIGNES: Record<Etape, string> = {
  relecture:
    "Comparez la lecture de la machine avec les pages, corrigez-la, mettez les volets en ordre, cochez chacun, puis confirmez.",
  controle: "Lisez la Transcription d'un autre agent contre les pages : acceptez-la, ou renvoyez-la avec une note.",
  validation:
    "Vérifiez les faits que la machine a lus : acceptez, corrigez ou rejetez chaque proposition. Seul ce que vous acceptez entre dans le dossier.",
};

function ListeDeTaches({ etape, taches }: { etape: Etape; taches: Tache[] }) {
  const id = `etape-${etape}`;
  const restantes = taches.filter((t) => !estFaite(t)).length;
  return (
    <section className="rel-carte" aria-labelledby={id}>
      <div className="rel-carte-tete">
        <h2 className="lf-app-sous-titre-fort" id={id}>
          {`${LIBELLES_DES_ETAPES[etape]}s`}
        </h2>
        <p className="rel-meta">{restantes ? `${pluriel(restantes, "à faire", "à faire")} sur ${taches.length}` : "Toutes faites"}</p>
      </div>
      <p className="rel-meta">{CONSIGNES[etape]}</p>
      <ol className="rel-taches">
        {taches.map((tache, i) => (
          <li key={tache.id} className={estFaite(tache) ? "rel-tache is-faite" : "rel-tache"}>
            <span className="rel-tache-rang rel-chiffres" aria-hidden="true">
              {i + 1}
            </span>
            <div className="rel-tache-texte">
              <p className="rel-tache-type">
                <Icon name={iconeDuType(tache.document.type)} size={20} />
                <span>{libelleDuDocument(tache.document)}</span>
              </p>
              <p className="rel-meta">{descriptionDuDocument(tache.document).split(" · ").slice(1).join(" · ")}</p>
            </div>
            <EtatDeTache tache={tache} />
            {!estFaite(tache) ? (
              <a className="rel-tache-lien" href={`/taches/${encodeURIComponent(tache.id)}`}>
                {tache.renvoyee ? "Reprendre" : tache.statut === "en-cours" ? "Continuer" : "Ouvrir"}
                <span className="rel-masque">{` : ${LIBELLES_DES_ETAPES[etape].toLowerCase()} ${i + 1}`}</span>
              </a>
            ) : (
              <span aria-hidden="true" />
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}

/** Le suivi de l'agent de relecture : les comptes de la semaine, puis l'historique. */
function SuiviDeLAgent({ suivi }: { suivi: Suivi }) {
  const comptes: [number, string, string, "clock" | "check" | "arrow-left" | "eye"][] = [
    [suivi.semaine.a_relire, "à relire", "à relire", "clock"],
    [suivi.semaine.confirmees, "confirmée", "confirmées", "check"],
    [suivi.semaine.renvoyees, "renvoyée par le Contrôle", "renvoyées par le Contrôle", "arrow-left"],
    [suivi.semaine.controlees, "contrôlée", "contrôlées", "eye"],
  ];
  return (
    <section className="rel-carte" aria-labelledby="suivi">
      <h2 className="lf-app-sous-titre-fort" id="suivi">
        Mon suivi
      </h2>
      <ul className="rel-comptes" aria-label="Cette semaine">
        {comptes.map(([n, un, plusieurs, icone]) => (
          <li key={un} className="rel-compte">
            <Icon name={icone} size={20} />
            <span className="rel-compte-nombre rel-chiffres">{n}</span>
            <span>{n > 1 ? plusieurs : un}</span>
          </li>
        ))}
      </ul>
      <h3 className="rel-sous-titre">Historique</h3>
      {suivi.historique.length === 0 ? (
        <p className="rel-meta">Rien encore : vos Relectures et Contrôles faits s'inscriront ici.</p>
      ) : (
        <table className="rel-historique">
          <thead>
            <tr>
              <th scope="col">Date</th>
              <th scope="col">Étape</th>
              <th scope="col">Issue</th>
            </tr>
          </thead>
          <tbody>
            {suivi.historique.map((e) => (
              <tr key={`${e.etape}-${e.id}`}>
                <td className="rel-chiffres">{formatDate(e.date)}</td>
                <td>{LIBELLES_DES_ETAPES[e.etape]}</td>
                <td>{libelleDeLIssue(e.issue)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

/**
 * L'accueil. Sans session : l'état du service et « Se connecter ». Avec : « Ma semaine », les tâches
 * confiées, par étape, où l'on en est, et, pour l'agent de relecture, son suivi.
 */
export default async function MaSemaine({ searchParams }: Parametres) {
  await connection();
  const relecteur = await lireRelecteur();
  if (!relecteur) return <EtatDeLActeur titre={TITRE} service={ACTEUR} avecConnexion />;
  const { fait } = await searchParams;
  const soignant = estSoignant(relecteur);

  const [semaine, suivi] = await Promise.all([lireMaSemaine(), soignant ? Promise.resolve(null) : lireSuivi()]);
  if (!semaine.ok) {
    if (semaine.statut === 401) redirect("/connexion");
    return (
      <Bureau relecteur={relecteur} titre="Ma semaine">
        <Refus statut={semaine.statut === 404 ? 500 : semaine.statut} ici="/" />
      </Bureau>
    );
  }

  const taches = semaine.corps;
  const faites = taches.filter(estFaite).length;
  const prochaine = taches.find((tache) => !estFaite(tache));
  const renvoyees = taches.filter((t) => t.renvoyee && !estFaite(t)).length;
  const message = typeof fait === "string" ? FAITS[fait] : undefined;

  return (
    <Bureau relecteur={relecteur} titre="Ma semaine">
      {message && (
        <Alert tone="succes" title={message}>
          {prochaine ? "La suivante vous attend." : "C'était la dernière de la semaine."}
        </Alert>
      )}

      {renvoyees > 0 && (
        <Alert tone="attention" title={`${pluriel(renvoyees, "Transcription renvoyée", "Transcriptions renvoyées")} par le Contrôle.`}>
          Le contrôleur a laissé une note en tête de chacune : reprenez-les en premier.
        </Alert>
      )}

      {taches.length === 0 ? (
        <section className="rel-carte rel-vide" aria-labelledby="rien-a-faire">
          <span className="rel-vide-marque" aria-hidden="true">
            <Icon name="check" size={40} />
          </span>
          <h2 className="lf-app-sous-titre-fort" id="rien-a-faire">
            Rien à faire cette semaine.
          </h2>
          <p className="rel-meta">
            {soignant
              ? "Aucune Extraction n'attend de validation pour l'instant. Revenez plus tard : les Transcriptions relues arrivent au fil de la semaine."
              : "Aucune tâche ne vous est confiée cette semaine. Votre quota arrive au début de la semaine suivante."}
          </p>
        </section>
      ) : (
        <>
          <section className="rel-carte" aria-labelledby="avancement">
            <h2 className="lf-app-sous-titre-fort" id="avancement">
              {soignant ? "Validation des Extractions" : "Relecture des Documents"}
            </h2>
            <Avancement faites={faites} total={taches.length} echeance={echeanceDeLaSemaine(taches)} />
            {prochaine ? (
              <div className="rel-actions">
                <Button href={`/taches/${encodeURIComponent(prochaine.id)}`} size="pro" icon={soignant ? "stethoscope" : "eye"}>
                  {faites === 0 ? "Commencer" : "Continuer"}
                </Button>
                <span className="rel-meta">{`${LIBELLES_DES_ETAPES[prochaine.etape]} · ${descriptionDuDocument(prochaine.document)}`}</span>
              </div>
            ) : (
              <Alert tone="succes" title="Semaine terminée : toutes vos tâches sont faites.">
                Merci. Les tâches de la semaine prochaine arriveront le lundi.
              </Alert>
            )}
          </section>

          {ORDRE_DES_ETAPES.map((etape) => {
            const deLEtape = taches.filter((t) => t.etape === etape);
            return deLEtape.length ? <ListeDeTaches key={etape} etape={etape} taches={deLEtape} /> : null;
          })}
        </>
      )}

      {suivi?.ok && <SuiviDeLAgent suivi={suivi.corps} />}
    </Bureau>
  );
}
