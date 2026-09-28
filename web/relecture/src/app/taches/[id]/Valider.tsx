"use client";

// La validation clinique : chaque proposition de la machine, avec ce qu'elle a lu et sa confiance, à
// accepter, corriger ou rejeter. Tout part ensemble ; l'écran dit ensuite ce qui est entré au dossier.
import { Alert, Button, Icon } from "@lafia/design";
import { useActionState, useState, type FormEvent } from "react";

import { confiance, genreDeProposition, pluriel } from "../../../libelles";
import type { Proposition } from "../../../types";
import { validerLaTache, type IssueDeLaValidation } from "../../actions";

type Choix = "accepter" | "corriger" | "rejeter";
type Decisions = Record<string, { decision?: Choix; valeur: string }>;

const CHOIX: { code: Choix; libelle: string; fait: string }[] = [
  { code: "accepter", libelle: "Accepter", fait: "Accepté" },
  { code: "corriger", libelle: "Corriger", fait: "Corrigé" },
  { code: "rejeter", libelle: "Rejeter", fait: "Rejeté" },
];

const ERREURS: Record<Extract<IssueDeLaValidation, { validee: false }>["erreur"], string> = {
  incomplet: "Chaque proposition attend une décision, et chaque correction une valeur.",
  service: "Le service relecture ne répond pas : rien n'est entré au dossier. Réessayez dans un instant ; vos décisions sont gardées.",
  indisponible: "Cette tâche n'est plus disponible : elle a pu être validée par un autre soignant. Rien n'est entré au dossier de votre part.",
  refusee: "Le service a refusé une des décisions : vérifiez les valeurs corrigées, puis validez à nouveau.",
};

const ICONE_DE_CONFIANCE = { elevee: "check", moyenne: "info", faible: "warning" } as const;

function Confiance({ valeur }: { valeur: number }) {
  const { mot, pourcent, niveau } = confiance(valeur);
  return (
    <span className={`rel-confiance rel-confiance--${niveau}`}>
      <Icon name={ICONE_DE_CONFIANCE[niveau]} size={16} />
      <span>{`${mot} · ${pourcent} %`}</span>
    </span>
  );
}

function CarteDeProposition({
  proposition,
  rang,
  choix,
  onChoisir,
  onCorriger,
}: {
  proposition: Proposition;
  rang: number;
  choix: Decisions[string];
  onChoisir: (decision: Choix) => void;
  onCorriger: (valeur: string) => void;
}) {
  const genre = genreDeProposition(proposition.type);
  const nom = `decision-${proposition.id}`;
  const fait = CHOIX.find((c) => c.code === choix.decision)?.fait;
  return (
    <li className={choix.decision ? `rel-proposition is-${choix.decision}` : "rel-proposition"}>
      <fieldset className="rel-proposition-corps">
        <legend className="rel-proposition-genre">
          <Icon name={genre.icone} size={20} />
          <span>{`${genre.libelle} · proposition ${rang}`}</span>
        </legend>
        <div className="rel-proposition-tete">
          <p className="rel-proposition-libelle">{proposition.libelle}</p>
          <p className={choix.decision === "corriger" || choix.decision === "rejeter" ? "rel-proposition-valeur is-barree" : "rel-proposition-valeur"}>
            {proposition.valeur ?? "Sans valeur lue"}
          </p>
          {proposition.confiance != null && <Confiance valeur={proposition.confiance} />}
        </div>
        {proposition.extrait && (
          <figure className="rel-extrait">
            <figcaption>Lu sur la page</figcaption>
            <blockquote>{`« ${proposition.extrait} »`}</blockquote>
          </figure>
        )}
        <div className="rel-decisions">
          {CHOIX.map((c) => (
            <label key={c.code} className={`rel-decision rel-decision--${c.code}`}>
              <input
                type="radio"
                name={nom}
                value={c.code}
                checked={choix.decision === c.code}
                onChange={() => onChoisir(c.code)}
              />
              {c.code !== "corriger" && <Icon name={c.code === "accepter" ? "check" : "x"} size={20} />}
              <span>{c.libelle}</span>
            </label>
          ))}
        </div>
        {choix.decision === "corriger" && (
          <div className="lf-field lf-field--pro rel-correction">
            <label className="lf-field-label" htmlFor={`valeur-${proposition.id}`}>
              Valeur juste, telle que la page la montre
            </label>
            <input
              id={`valeur-${proposition.id}`}
              className="lf-input"
              value={choix.valeur}
              onChange={(e) => onCorriger(e.target.value)}
              autoFocus
              required
              autoComplete="off"
            />
          </div>
        )}
        {fait && (
          <p className="rel-proposition-fait">
            <Icon name={choix.decision === "rejeter" ? "x" : "check"} size={18} />
            <span>
              {choix.decision === "rejeter"
                ? "Rejeté : n'entrera pas au dossier."
                : `${fait} : entrera au dossier${choix.decision === "corriger" && choix.valeur.trim() ? ` avec « ${choix.valeur.trim()} »` : ""}.`}
            </span>
          </p>
        )}
      </fieldset>
    </li>
  );
}

/** Ce qui est entré au dossier, et ce qui est resté dans la tâche. */
function Confirmation({
  propositions,
  decisions,
  suivante,
}: {
  propositions: Proposition[];
  decisions: Decisions;
  suivante: string | null;
}) {
  const entrees = propositions.filter((p) => decisions[p.id]?.decision !== "rejeter");
  const rejetees = propositions.filter((p) => decisions[p.id]?.decision === "rejeter");
  return (
    <section className="rel-carte rel-confirmation" aria-labelledby="validation-enregistree" tabIndex={-1} ref={(el) => el?.focus()}>
      <span className="rel-vide-marque" aria-hidden="true">
        <Icon name="check" size={40} />
      </span>
      <h2 className="lf-app-sous-titre-fort" id="validation-enregistree">
        Validation enregistrée.
      </h2>
      {entrees.length > 0 ? (
        <>
          <p className="rel-meta">
            {`${pluriel(entrees.length, "fait est entré", "faits sont entrés")} dans le dossier, avec l'origine « extraction » et votre nom comme soignant qui l'a validé :`}
          </p>
          <ul className="rel-entrees">
            {entrees.map((p) => {
              const choix = decisions[p.id];
              const corrige = choix?.decision === "corriger";
              return (
                <li key={p.id}>
                  <Icon name={genreDeProposition(p.type).icone} size={20} />
                  <span>
                    <strong>{p.libelle}</strong>
                    {` : ${corrige ? choix.valeur.trim() : (p.valeur ?? "sans valeur")}`}
                    {corrige && <span className="rel-meta">{` (corrigé, la machine avait lu « ${p.valeur ?? "rien"} »)`}</span>}
                  </span>
                </li>
              );
            })}
          </ul>
        </>
      ) : (
        <p className="rel-meta">Rien n'est entré dans le dossier.</p>
      )}
      {rejetees.length > 0 && (
        <p className="rel-meta">
          {`${pluriel(rejetees.length, "proposition rejetée reste", "propositions rejetées restent")} dans la tâche seulement, pour mesurer le modèle.`}
        </p>
      )}
      <div className="rel-actions">
        {suivante ? (
          <Button href={`/taches/${encodeURIComponent(suivante)}`} size="pro" icon="stethoscope">
            Tâche suivante
          </Button>
        ) : (
          <Button href="/?fait=validation" size="pro" icon="list">
            Revenir à ma semaine
          </Button>
        )}
        {suivante && (
          <Button href="/" size="pro" variant="ghost" icon="list">
            Ma semaine
          </Button>
        )}
      </div>
    </section>
  );
}

export function Valider({ tache, propositions }: { tache: string; propositions: Proposition[] }) {
  const [issue, envoyer, enCours] = useActionState(validerLaTache, null);
  const [decisions, setDecisions] = useState<Decisions>(() =>
    Object.fromEntries(propositions.map((p) => [p.id, { valeur: p.valeur ?? "" }])),
  );
  const [manque, setManque] = useState<string | null>(null);

  if (issue?.validee) return <Confirmation propositions={propositions} decisions={decisions} suivante={issue.suivante} />;

  const decidees = propositions.filter((p) => {
    const choix = decisions[p.id];
    return choix?.decision && (choix.decision !== "corriger" || choix.valeur.trim());
  }).length;
  const envoi = propositions.map((p) => {
    const choix = decisions[p.id];
    return choix.decision === "corriger"
      ? { id: p.id, decision: choix.decision, valeur: choix.valeur }
      : { id: p.id, decision: choix.decision };
  });

  function verifier(evenement: FormEvent<HTMLFormElement>) {
    const reste = propositions.length - decidees;
    if (reste > 0) {
      evenement.preventDefault();
      setManque(`Il reste ${pluriel(reste, "proposition")} sans décision complète. Chacune doit être acceptée, corrigée ou rejetée.`);
      return;
    }
    setManque(null);
  }

  function changer(id: string, changement: Partial<Decisions[string]>) {
    setDecisions((deja) => ({ ...deja, [id]: { ...deja[id], ...changement } }));
    setManque(null);
  }

  return (
    <form action={envoyer} onSubmit={verifier} className="rel-validation">
      <input type="hidden" name="tache" value={tache} />
      <input type="hidden" name="decisions" value={JSON.stringify(envoi)} />

      {propositions.length === 0 ? (
        <p className="rel-meta">
          La machine n'a proposé aucun fait pour ce Document. Terminez la tâche : rien n'entrera au dossier.
        </p>
      ) : (
        <ol className="rel-propositions">
          {propositions.map((p, i) => (
            <CarteDeProposition
              key={p.id}
              proposition={p}
              rang={i + 1}
              choix={decisions[p.id]}
              onChoisir={(decision) => changer(p.id, { decision })}
              onCorriger={(valeur) => changer(p.id, { valeur })}
            />
          ))}
        </ol>
      )}

      {(manque || (issue && !issue.validee)) && (
        <Alert tone="danger" title={manque ?? (issue && !issue.validee ? ERREURS[issue.erreur] : "")} />
      )}

      <div className="rel-envoi">
        {propositions.length > 0 && (
          <p className="rel-meta rel-chiffres" aria-live="polite">{`${decidees} / ${propositions.length} décidées`}</p>
        )}
        <Button type="submit" size="pro" icon="check" loading={enCours}>
          {propositions.length === 0
            ? "Terminer la tâche"
            : `Valider ${propositions.length > 1 ? `les ${propositions.length} décisions` : "la décision"}`}
        </Button>
      </div>
    </form>
  );
}
