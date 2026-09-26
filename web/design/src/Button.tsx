import type { AnchorHTMLAttributes, ButtonHTMLAttributes, ReactNode } from "react";

import type { NomIcone } from "./generes/icones";
import { Icon } from "./Icon";
import { cx } from "./svg";

type Commun = {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  /** `citizen` : cible de 48px, 18px ; `pro` : 40px, 16px. */
  size?: "citizen" | "pro";
  icon?: NomIcone;
  iconRight?: NomIcone;
  loading?: boolean;
  block?: boolean;
  className?: string;
  children: ReactNode;
};
type EnBouton = Commun & Omit<ButtonHTMLAttributes<HTMLButtonElement>, keyof Commun> & { href?: undefined };
type EnLien = Commun & Omit<AnchorHTMLAttributes<HTMLAnchorElement>, keyof Commun> & { href: string };

/** Bouton, ou lien qui en a l'allure quand il porte un `href`. Infinitif : « Encaisser ». */
export function Button(props: EnBouton | EnLien) {
  const { variant = "primary", size = "citizen", icon, iconRight, loading, block, className, children, ...natifs } = props;
  const classes = cx("lf-btn", `lf-btn--${variant}`, `lf-btn--${size}`, block && "lf-btn--block", loading && "is-loading", className);
  const taille = size === "pro" ? 20 : 24;
  const contenu = (
    <>
      {icon && <Icon name={icon} size={taille} />}
      <span className="lf-btn-label">{children}</span>
      {iconRight && <Icon name={iconRight} size={taille} />}
    </>
  );
  if (natifs.href !== undefined) {
    return (
      <a {...(natifs as AnchorHTMLAttributes<HTMLAnchorElement>)} className={classes}>
        {contenu}
      </a>
    );
  }
  const bouton = natifs as ButtonHTMLAttributes<HTMLButtonElement>;
  return (
    <button
      type="button"
      {...bouton}
      className={classes}
      disabled={bouton.disabled || loading}
      aria-busy={loading || undefined}
    >
      {contenu}
    </button>
  );
}
