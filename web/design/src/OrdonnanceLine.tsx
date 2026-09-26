"use client";

import { useId, type ReactNode } from "react";

import { formatFcfa } from "./formats";
import { Icon } from "./Icon";
import { Picto } from "./Picto";
import { Posology, StatusBadge, type Posologie, type Status } from "./statuts";
import { cx } from "./svg";

/**
 * Ligne d'ordonnance. `citoyen` : lecture, posologie en pictogrammes. `caisse` et `pharmacie` : une
 * case à cocher, pour encaisser ou remettre la ligne ; `name` et `value` l'envoient avec le formulaire.
 */
export function OrdonnanceLine({
  name,
  value,
  detail,
  mode = "citoyen",
  price,
  status,
  posology,
  allergy,
  checked,
  onToggle,
  disabled,
  className,
  children,
}: {
  name?: string;
  value?: string;
  detail?: string;
  mode?: "citoyen" | "caisse" | "pharmacie";
  price?: number;
  status?: Status;
  posology?: Posologie;
  allergy?: string;
  checked?: boolean;
  onToggle?: (coche: boolean) => void;
  disabled?: boolean;
  className?: string;
  /** Le nom du produit ou de l'acte. */
  children: ReactNode;
}) {
  const id = useId();
  const principal = (
    <div className="lf-line-main">
      <div className="lf-line-name">{children}</div>
      {detail && <div className="lf-line-detail">{detail}</div>}
      {posology && mode === "citoyen" && <Posology {...posology} />}
      {allergy && (
        <div className="lf-line-allergy">
          <Picto name="allergie" size={20} decorative />
          <span>{allergy}</span>
        </div>
      )}
    </div>
  );
  const cote = (
    <div className="lf-line-side">
      {price != null && <div className="lf-line-price">{formatFcfa(price)}</div>}
      {status && <StatusBadge status={status} size={mode === "citoyen" ? "citizen" : "pro"} />}
    </div>
  );
  const classes = cx(
    "lf-line",
    `lf-line--${mode}`,
    checked && "is-checked",
    disabled && "is-disabled",
    Boolean(allergy) && "has-allergy",
    className,
  );

  if (mode === "citoyen") {
    return (
      <div className={classes}>
        {principal}
        {cote}
      </div>
    );
  }
  return (
    <label className={classes} htmlFor={id}>
      <input
        id={id}
        type="checkbox"
        className="lf-check"
        name={name}
        value={value}
        checked={onToggle ? Boolean(checked) : undefined}
        defaultChecked={onToggle ? undefined : checked}
        disabled={disabled}
        onChange={onToggle ? () => onToggle(!checked) : undefined}
      />
      <span className="lf-check-box" aria-hidden="true">
        <Icon name="check" size={16} />
      </span>
      {principal}
      {cote}
    </label>
  );
}
