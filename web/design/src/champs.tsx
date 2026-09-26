"use client";

// Champs de saisie. Chacun marche dans un simple formulaire HTML envoyé à un service : ce qu'il envoie
// est ce que le service attend (un NPI en treize chiffres, jamais groupé), avant comme après le
// chargement du JavaScript. Ce qui a été tapé avant le chargement est repris, pas effacé.

import { useEffect, useId, useRef, useState, type InputHTMLAttributes, type ReactNode, type RefObject } from "react";

import { LONGUEUR_NPI, formatNpi } from "./formats";
import type { NomIcone } from "./generes/icones";
import { Icon } from "./Icon";
import { cx } from "./svg";

type Taille = "citizen" | "pro";

function Field({
  id,
  label,
  hint,
  error,
  size = "citizen",
  className,
  children,
}: {
  id: string;
  label: ReactNode;
  hint?: ReactNode;
  error?: ReactNode;
  size?: Taille;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div className={cx("lf-field", `lf-field--${size}`, Boolean(error) && "has-error", className)}>
      <label className="lf-field-label" htmlFor={id}>
        {label}
      </label>
      {hint && (
        <p className="lf-field-hint" id={`${id}-hint`}>
          {hint}
        </p>
      )}
      {children}
      {error && (
        <p className="lf-field-error" id={`${id}-err`} role="alert">
          <Icon name="warning-octagon" size={20} />
          <span>{error}</span>
        </p>
      )}
    </div>
  );
}

function decritPar(id: string, hint?: ReactNode, error?: ReactNode): string | undefined {
  return [hint && `${id}-hint`, error && `${id}-err`].filter(Boolean).join(" ") || undefined;
}

/** Ce que le champ contenait déjà au chargement du JavaScript, tapé pendant qu'il arrivait. */
function useSaisieDejaFaite(ref: RefObject<HTMLInputElement | null>, reprendre: (valeur: string) => void) {
  useEffect(() => {
    const deja = ref.current?.value;
    if (deja) reprendre(deja);
    // Une seule fois, au chargement.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}

type ProprietesTexte = {
  label: ReactNode;
  hint?: ReactNode;
  error?: ReactNode;
  size?: Taille;
  icon?: NomIcone;
  className?: string;
} & Omit<InputHTMLAttributes<HTMLInputElement>, "size" | "className">;

/** Champ texte : libellé toujours visible, aide et erreur reliées au champ. */
export function TextInput({ label, hint, error, size, icon, className, id, ...natifs }: ProprietesTexte) {
  const auto = useId();
  const identifiant = id ?? auto;
  return (
    <Field id={identifiant} label={label} hint={hint} error={error} size={size} className={className}>
      <div className="lf-input-wrap">
        {icon && <Icon name={icon} size={20} className="lf-input-icon" />}
        <input
          {...natifs}
          id={identifiant}
          className="lf-input"
          aria-invalid={error ? true : undefined}
          aria-describedby={decritPar(identifiant, hint, error)}
        />
      </div>
    </Field>
  );
}

/**
 * NPI : treize chiffres, affichés en groupes 4-3-3-3 pour la lecture à voix haute. Le formulaire
 * reçoit sous `name` les chiffres seuls, ce que identite et les services attendent.
 */
export function NpiField({
  name,
  value,
  defaultValue = "",
  onChange,
  onComplete,
  label = "NPI",
  hint,
  error,
  size,
  autoFocus,
  required,
  className,
}: {
  name?: string;
  value?: string;
  defaultValue?: string;
  onChange?: (chiffres: string) => void;
  onComplete?: (npi: string) => void;
  label?: ReactNode;
  hint?: ReactNode;
  error?: ReactNode;
  size?: Taille;
  autoFocus?: boolean;
  required?: boolean;
  className?: string;
}) {
  const id = useId();
  const champ = useRef<HTMLInputElement>(null);
  const [interne, setInterne] = useState(defaultValue);
  const [charge, setCharge] = useState(false);
  const chiffres = (value ?? interne).replace(/\D/g, "").slice(0, LONGUEUR_NPI);
  const complet = chiffres.length === LONGUEUR_NPI;
  const etaitComplet = useRef(complet);

  function changer(saisie: string) {
    const nouveaux = saisie.replace(/\D/g, "").slice(0, LONGUEUR_NPI);
    if (value === undefined) setInterne(nouveaux);
    onChange?.(nouveaux);
  }
  useSaisieDejaFaite(champ, changer);
  useEffect(() => setCharge(true), []);
  useEffect(() => {
    if (complet && !etaitComplet.current) onComplete?.(chiffres);
    etaitComplet.current = complet;
  }, [complet, chiffres, onComplete]);

  return (
    <Field id={id} label={label} hint={hint} error={error} size={size} className={cx("lf-npi", complet && "is-complete", className)}>
      <div className="lf-input-wrap">
        <Icon name="identification-card" size={24} className="lf-input-icon" />
        <input
          ref={champ}
          id={id}
          // Avant le chargement, le champ visible porte lui-même le nom : le formulaire marche sans JavaScript.
          name={charge ? undefined : name}
          className="lf-input lf-input--id"
          inputMode="numeric"
          autoComplete="off"
          placeholder="0000 000 000 000"
          value={formatNpi(chiffres)}
          onChange={(e) => changer(e.target.value)}
          autoFocus={autoFocus}
          required={required}
          pattern={"[0-9]{4} ?[0-9]{3} ?[0-9]{3} ?[0-9]{3}"}
          title="Treize chiffres"
          aria-invalid={error ? true : undefined}
          aria-describedby={decritPar(id, hint, error)}
        />
        <span className="lf-npi-state" aria-live="polite">
          {complet ? <Icon name="check" size={20} label="NPI complet" /> : <span className="lf-npi-count">{`${chiffres.length}/${LONGUEUR_NPI}`}</span>}
        </span>
      </div>
      {charge && name && <input type="hidden" name={name} value={chiffres} />}
    </Field>
  );
}

/**
 * Code carnet, case par case, en deux groupes comme sur le reçu : `H3T-9QR`. Majuscules, sans tiret ;
 * identite normalise de même la saisie.
 */
export function CodeField({
  name,
  length = 6,
  value,
  defaultValue = "",
  onChange,
  numeric = false,
  label = "Code carnet",
  hint,
  error,
  size,
  required,
  className,
}: {
  name?: string;
  length?: number;
  value?: string;
  defaultValue?: string;
  onChange?: (code: string) => void;
  numeric?: boolean;
  label?: ReactNode;
  hint?: ReactNode;
  error?: ReactNode;
  size?: Taille;
  required?: boolean;
  className?: string;
}) {
  const id = useId();
  const champ = useRef<HTMLInputElement>(null);
  const [interne, setInterne] = useState(defaultValue);
  const [focus, setFocus] = useState(false);
  const nettoyer = (saisie: string) => saisie.toUpperCase().replace(/[^0-9A-Z]/g, "").slice(0, length);
  const code = nettoyer(value ?? interne);

  function changer(saisie: string) {
    const nouveau = nettoyer(saisie);
    if (value === undefined) setInterne(nouveau);
    onChange?.(nouveau);
  }
  useSaisieDejaFaite(champ, changer);

  const moitie = Math.ceil(length / 2);
  const cases = Array.from({ length }, (_, i) => (
    <span key={i} className={cx("lf-code-cell", Boolean(code[i]) && "is-filled", focus && i === Math.min(code.length, length - 1) && "is-caret")}>
      {code[i] ?? ""}
    </span>
  ));

  return (
    <Field id={id} label={label} hint={hint} error={error} size={size} className={cx("lf-code", className)}>
      <div className="lf-code-row">
        <input
          ref={champ}
          id={id}
          name={name}
          className="lf-code-input"
          value={code}
          onChange={(e) => changer(e.target.value)}
          inputMode={numeric ? "numeric" : "text"}
          autoComplete="one-time-code"
          autoCapitalize="characters"
          spellCheck={false}
          required={required}
          onFocus={() => setFocus(true)}
          onBlur={() => setFocus(false)}
          aria-invalid={error ? true : undefined}
          aria-describedby={decritPar(id, hint, error)}
        />
        <div className="lf-code-cells" aria-hidden="true">
          <span className="lf-code-group">{cases.slice(0, moitie)}</span>
          <span className="lf-code-sep">-</span>
          <span className="lf-code-group">{cases.slice(moitie)}</span>
        </div>
      </div>
    </Field>
  );
}
