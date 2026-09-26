"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

import { Icon } from "./Icon";
import { cx } from "./svg";

/** Une valeur à recopier : identifiant, mot de passe, NPI ou code carnet de démonstration. */
export type CompteAffiche = Array<{ label: string; value: string }>;

function LigneACopier({ label, value }: { label: string; value: string }) {
  const [etat, setEtat] = useState<"repos" | "copie" | "selectionne">("repos");
  const valeur = useRef<HTMLElement>(null);
  const minuteur = useRef<ReturnType<typeof setTimeout>>(undefined);
  useEffect(() => () => clearTimeout(minuteur.current), []);

  function selectionner() {
    // Sans presse-papiers (page non sécurisée, refus du navigateur) : la valeur reste sélectionnée.
    const plage = document.createRange();
    if (valeur.current) plage.selectNodeContents(valeur.current);
    getSelection()?.removeAllRanges();
    getSelection()?.addRange(plage);
    setEtat("selectionne");
  }
  async function copier() {
    try {
      await navigator.clipboard.writeText(value);
      setEtat("copie");
    } catch {
      selectionner();
    }
    clearTimeout(minuteur.current);
    minuteur.current = setTimeout(() => setEtat("repos"), 1600);
  }

  return (
    <div className="lf-demo-row">
      <span className="lf-demo-k">{label}</span>
      <code className="lf-demo-v" ref={valeur}>
        {value}
      </code>
      <button type="button" className={cx("lf-copy", etat === "copie" && "is-done")} onClick={copier}>
        <Icon name={etat === "copie" ? "check" : "copy"} size={18} />
        <span aria-live="polite">{etat === "copie" ? "Copié" : etat === "selectionne" ? "Sélectionné" : "Copier"}</span>
      </button>
    </div>
  );
}

/**
 * Comptes de démonstration, repliés sous « Essayer avec un compte de démonstration ». Ils sont
 * publics : tout le jeu de données est fictif.
 */
export function DemoAccount({
  comptes,
  note,
  open,
  summary = "Essayer avec un compte de démonstration",
}: {
  comptes: CompteAffiche[];
  note?: ReactNode;
  open?: boolean;
  summary?: string;
}) {
  return (
    <details className="lf-demo" open={open}>
      <summary>
        <Icon name="lock-simple" size={20} />
        <span>{summary}</span>
        <Icon name="caret-down" size={18} className="lf-demo-caret" />
      </summary>
      <div className="lf-demo-body">
        {comptes.map((compte, i) => (
          <div key={i} className="lf-demo-account">
            {compte.map((ligne) => (
              <LigneACopier key={ligne.label} {...ligne} />
            ))}
          </div>
        ))}
        {note && <p className="lf-demo-note">{note}</p>}
      </div>
    </details>
  );
}
