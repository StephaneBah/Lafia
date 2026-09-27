"use client";

// Le verdict du triage : un grand bouton par verdict, icône et mot. « Type à corriger » demande d'abord
// le bon type. L'année se corrige au besoin, avant de choisir. Le verdict parti, la tâche suivante s'ouvre.
import { Icon, TextInput } from "@lafia/design";
import { useActionState, useState } from "react";
import { useFormStatus } from "react-dom";

import { ANNEE_MIN, libelleDuType, TYPES_DE_DOCUMENT, VERDICTS } from "../../../libelles";
import { trierLaTache, type RefusDuTriage } from "../../actions";

const MESSAGES: Record<NonNullable<RefusDuTriage>["erreur"], string> = {
  annee: `L'année s'écrit en quatre chiffres, de ${ANNEE_MIN} à l'année en cours. Laissez le champ vide si elle est juste.`,
  type: "Choisissez le bon type de document.",
  verdict: "Le service n'a pas accepté ce verdict. Choisissez-en un autre, ou réessayez.",
  service: "Le service relecture ne répond pas : le verdict n'est pas enregistré. Réessayez dans un instant.",
  indisponible: "Cette tâche n'est plus disponible : elle a pu revenir au lot commun. Revenez à votre semaine.",
};

function BoutonDeVerdict({ code, libelle, aide, icone }: (typeof VERDICTS)[number]) {
  const { pending, data } = useFormStatus();
  const envoye = pending && data?.get("verdict") === code;
  return (
    <button
      type="submit"
      name="verdict"
      value={code}
      className={`rel-verdict rel-verdict--${code}`}
      disabled={pending}
      aria-busy={envoye || undefined}
    >
      <span className="rel-verdict-marque" aria-hidden="true">
        <Icon name={icone} size={28} />
      </span>
      <span className="rel-verdict-texte">
        <span className="rel-verdict-mot">{envoye ? "Enregistrement…" : libelle}</span>
        <span className="rel-verdict-aide">{aide}</span>
      </span>
    </button>
  );
}

function ChoixDuType({ declare, onAnnuler }: { declare: string; onAnnuler: () => void }) {
  const { pending } = useFormStatus();
  return (
    <fieldset className="rel-choix-type">
      <legend className="rel-legende">
        <Icon name="list" size={22} />
        <span>Quel est le bon type ?</span>
      </legend>
      <p className="rel-meta">{`Déclaré au dépôt : ${libelleDuType(declare)}.`}</p>
      <div className="rel-tuiles">
        {TYPES_DE_DOCUMENT.filter((type) => type.code !== declare).map((type) => (
          <label key={type.code} className="rel-tuile">
            <input type="radio" name="type" value={type.code} required />
            <Icon name={type.icone} size={28} />
            <span>{type.libelle}</span>
          </label>
        ))}
      </div>
      <div className="rel-actions">
        <button type="submit" name="verdict" value="mauvais-type" className="lf-btn lf-btn--primary lf-btn--pro" disabled={pending}>
          <Icon name="check" size={20} />
          <span className="lf-btn-label">{pending ? "Enregistrement…" : "Enregistrer le bon type"}</span>
        </button>
        <button type="button" className="lf-btn lf-btn--ghost lf-btn--pro" onClick={onAnnuler} disabled={pending}>
          <Icon name="x" size={20} />
          <span className="lf-btn-label">Revenir aux verdicts</span>
        </button>
      </div>
    </fieldset>
  );
}

export function Trier({ tache, typeDeclare, anneeDeclaree }: { tache: string; typeDeclare: string; anneeDeclaree: string }) {
  const [refus, envoyer] = useActionState(trierLaTache, null);
  const [choixDuType, setChoixDuType] = useState(false);

  return (
    <form action={envoyer} className="rel-triage">
      <input type="hidden" name="tache" value={tache} />

      <TextInput
        label="Année corrigée (facultatif)"
        hint={`Déclarée au dépôt : ${anneeDeclaree}. Remplissez seulement si la page montre une autre année.`}
        name="annee"
        inputMode="numeric"
        maxLength={4}
        autoComplete="off"
        size="pro"
        className="rel-champ-annee"
        error={refus?.erreur === "annee" ? MESSAGES.annee : undefined}
      />

      {refus && refus.erreur !== "annee" && (
        <p className="rel-erreur" role="alert">
          <Icon name="warning-octagon" size={20} />
          <span>{MESSAGES[refus.erreur]}</span>
        </p>
      )}

      {choixDuType ? (
        <ChoixDuType declare={typeDeclare} onAnnuler={() => setChoixDuType(false)} />
      ) : (
        <fieldset className="rel-verdicts">
          <legend className="rel-legende">Ce document est…</legend>
          {VERDICTS.map((verdict) =>
            verdict.code === "mauvais-type" ? (
              <button
                key={verdict.code}
                type="button"
                className="rel-verdict rel-verdict--mauvais-type"
                onClick={() => setChoixDuType(true)}
              >
                <span className="rel-verdict-marque" aria-hidden="true">
                  <Icon name={verdict.icone} size={28} />
                </span>
                <span className="rel-verdict-texte">
                  <span className="rel-verdict-mot">{verdict.libelle}</span>
                  <span className="rel-verdict-aide">{verdict.aide}</span>
                </span>
              </button>
            ) : (
              <BoutonDeVerdict key={verdict.code} {...verdict} />
            ),
          )}
        </fieldset>
      )}
    </form>
  );
}
