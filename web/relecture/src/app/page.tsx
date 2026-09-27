import { EtatDeLActeur } from "@lafia/commun";
import { Alert, Button, formatDate, Icon } from "@lafia/design";
import { redirect } from "next/navigation";
import { connection } from "next/server";

import { ACTEUR, iconeDuType, libelleDeLisibilite, libelleDuType, pluriel, TITRE } from "../libelles";
import { estFaite, estSoignant, lireMaSemaine, lireRelecteur, type Tache } from "../relecture";
import { Bureau, Refus } from "./Bureau";
import { EtatDeTache } from "./EtatDeTache";

type Parametres = { searchParams: Promise<Record<string, string | string[] | undefined>> };

/** L'échéance de la semaine : la plus proche des tâches qui restent, sinon la dernière. */
function echeanceDeLaSemaine(taches: Tache[]): string | null {
  const restantes = taches.filter((tache) => !estFaite(tache)).map((tache) => tache.echeance);
  const dates = (restantes.length ? restantes : taches.map((tache) => tache.echeance)).filter(Boolean).sort();
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

/**
 * L'accueil. Sans session : l'état du service et « Se connecter ». Avec : « Ma semaine », les tâches
 * confiées au relecteur, où il en est, et par où continuer.
 */
export default async function MaSemaine({ searchParams }: Parametres) {
  await connection();
  const relecteur = await lireRelecteur();
  if (!relecteur) return <EtatDeLActeur titre={TITRE} service={ACTEUR} avecConnexion />;
  const { fait } = await searchParams;

  const semaine = await lireMaSemaine();
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
  const soignant = estSoignant(relecteur);
  const consigne = soignant
    ? "Vérifiez ce que la machine a lu dans chaque Document : acceptez, corrigez ou rejetez chaque proposition. Seul ce que vous acceptez entre dans le dossier."
    : "Regardez chaque Document et dites s'il est utilisable. Vous ne validez aucun fait médical : un médecin ou un infirmier le fera ensuite.";

  return (
    <Bureau relecteur={relecteur} titre="Ma semaine">
      {fait && (
        <Alert tone="succes" title="Tâche enregistrée.">
          {prochaine ? "La suivante vous attend." : "C'était la dernière de la semaine."}
        </Alert>
      )}

      {taches.length === 0 ? (
        <section className="rel-carte rel-vide" aria-labelledby="rien-a-faire">
          <span className="rel-vide-marque" aria-hidden="true">
            <Icon name="check" size={40} />
          </span>
          <h2 className="lf-app-sous-titre-fort" id="rien-a-faire">
            Rien à relire cette semaine.
          </h2>
          <p className="rel-meta">
            {soignant
              ? "Aucune Extraction n'attend de validation pour l'instant. Revenez plus tard : les Documents triés arrivent au fil de la semaine."
              : "Aucune tâche ne vous est confiée cette semaine. Votre quota arrive au début de la semaine suivante."}
          </p>
        </section>
      ) : (
        <>
          <section className="rel-carte" aria-labelledby="avancement">
            <h2 className="lf-app-sous-titre-fort" id="avancement">
              {soignant ? "Validation des Extractions" : "Triage des Documents"}
            </h2>
            <p className="rel-meta">{consigne}</p>
            <Avancement faites={faites} total={taches.length} echeance={echeanceDeLaSemaine(taches)} />
            {prochaine ? (
              <div className="rel-actions">
                <Button href={`/taches/${encodeURIComponent(prochaine.id)}`} size="pro" icon={soignant ? "stethoscope" : "eye"}>
                  {faites === 0 ? "Commencer" : "Continuer"}
                </Button>
              </div>
            ) : (
              <Alert tone="succes" title="Semaine terminée : toutes vos tâches sont faites.">
                Merci. Les tâches de la semaine prochaine arriveront le lundi.
              </Alert>
            )}
          </section>

          <section className="rel-carte" aria-labelledby="liste-des-taches">
            <h2 className="lf-app-sous-titre-fort" id="liste-des-taches">
              {`Les ${pluriel(taches.length, "tâche")} de la semaine`}
            </h2>
            <ol className="rel-taches">
              {taches.map((tache, i) => {
                const lisibilite = libelleDeLisibilite(tache.document.lisibilite);
                return (
                  <li key={tache.id} className={estFaite(tache) ? "rel-tache is-faite" : "rel-tache"}>
                    <span className="rel-tache-rang rel-chiffres" aria-hidden="true">
                      {i + 1}
                    </span>
                    <div className="rel-tache-texte">
                      <p className="rel-tache-type">
                        <Icon name={iconeDuType(tache.document.type)} size={20} />
                        <span>{libelleDuType(tache.document.type)}</span>
                      </p>
                      <p className="rel-meta">
                        {[tache.document.annee, pluriel(tache.document.pages, "page"), lisibilite].filter(Boolean).join(" · ")}
                      </p>
                    </div>
                    <EtatDeTache tache={tache} />
                    {!estFaite(tache) && (
                      <a className="rel-tache-lien" href={`/taches/${encodeURIComponent(tache.id)}`}>
                        {`Ouvrir`}
                        <span className="rel-masque">{` la tâche ${i + 1}`}</span>
                      </a>
                    )}
                  </li>
                );
              })}
            </ol>
          </section>
        </>
      )}
    </Bureau>
  );
}
