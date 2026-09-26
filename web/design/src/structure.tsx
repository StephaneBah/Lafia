// Composants de structure, sans état : le fil d'un cas de visite, les alertes, les cartes, les tableaux.

import type { CSSProperties, ElementType, ReactNode } from "react";

import type { NomIcone } from "./generes/icones";
import { Icon } from "./Icon";
import { Picto } from "./Picto";
import { cx } from "./svg";

/**
 * Étape d'un cas de visite sur le fil, dans `<ol className="lf-timeline">`. `animate` et `index` : le
 * fil se dessine étape par étape à l'ouverture de l'écran.
 */
export function TimelineItem({
  title,
  date,
  place,
  icon,
  state = "done",
  first,
  last,
  animate,
  index,
  className,
  children,
}: {
  title: ReactNode;
  date?: string;
  place?: string;
  icon?: NomIcone;
  state?: "done" | "current" | "upcoming";
  first?: boolean;
  last?: boolean;
  animate?: boolean;
  index?: number;
  className?: string;
  children?: ReactNode;
}) {
  return (
    <li
      className={cx("lf-tl", `lf-tl--${state}`, first && "is-first", last && "is-last", animate && "lf-tl--draw", className)}
      style={index != null ? ({ "--lf-i": index } as CSSProperties) : undefined}
      aria-current={state === "current" ? "step" : undefined}
    >
      <div className="lf-tl-rail" aria-hidden="true">
        <span className="lf-tl-fil" />
        <span className="lf-tl-node">{icon && <Icon name={icon} size={18} />}</span>
      </div>
      <div className="lf-tl-body">
        <div className="lf-tl-meta">
          {date && <time>{date}</time>}
          {place && <span>{place}</span>}
        </div>
        <div className="lf-tl-title">{title}</div>
        {children && <div className="lf-tl-content">{children}</div>}
      </div>
    </li>
  );
}

const MARQUES_D_ALERTE = {
  info: { icone: "info" },
  succes: { icone: "check" },
  attention: { icone: "warning" },
  danger: { icone: "warning-octagon" },
  allergie: { picto: "allergie" },
  urgence: { picto: "urgence" },
} as const;

/**
 * Alerte persistante. `allergie` et `urgence` entrent d'un seul mouvement ferme, ne clignotent jamais
 * et ne se ferment pas.
 */
export function Alert({
  tone = "info",
  title,
  actions,
  onClose,
  className,
  children,
}: {
  tone?: keyof typeof MARQUES_D_ALERTE;
  title?: ReactNode;
  actions?: ReactNode;
  onClose?: () => void;
  className?: string;
  children?: ReactNode;
}) {
  const marque = MARQUES_D_ALERTE[tone];
  const forte = tone === "allergie" || tone === "urgence";
  return (
    <div
      className={cx("lf-alert", `lf-alert--${tone}`, forte && "lf-alert--strong", className)}
      role={forte || tone === "danger" ? "alert" : "status"}
    >
      <div className="lf-alert-mark">
        {"picto" in marque ? <Picto name={marque.picto} size={40} decorative /> : <Icon name={marque.icone} size={24} />}
      </div>
      <div className="lf-alert-body">
        {title && <div className="lf-alert-title">{title}</div>}
        {children && <div className="lf-alert-text">{children}</div>}
        {actions && <div className="lf-alert-actions">{actions}</div>}
      </div>
      {onClose && !forte && (
        <button type="button" className="lf-iconbtn" onClick={onClose}>
          <Icon name="x" size={20} label="Fermer" />
        </button>
      )}
    </div>
  );
}

/** Carte blanche sur fond pâle. `loading` : placeholders à la forme du contenu, jamais un spinner seul. */
export function Card({
  tone,
  interactive,
  href,
  dense,
  loading,
  as,
  className,
  children,
}: {
  tone?: "soft" | "ardoise";
  interactive?: boolean;
  href?: string;
  dense?: boolean;
  loading?: boolean;
  as?: ElementType;
  className?: string;
  children?: ReactNode;
}) {
  const classes = cx(
    "lf-card",
    tone && `lf-card--${tone}`,
    (interactive || href) && "lf-card--interactive",
    dense && "lf-card--dense",
    className,
  );
  if (loading) {
    return (
      <div className={cx(classes, "is-loading")} aria-busy="true" aria-label="Chargement">
        <span className="lf-skel lf-skel--title" />
        <span className="lf-skel" />
        <span className="lf-skel lf-skel--short" />
      </div>
    );
  }
  if (href) {
    return (
      <a className={classes} href={href}>
        {children}
      </a>
    );
  }
  const Balise = as ?? "div";
  return <Balise className={classes}>{children}</Balise>;
}

export type Colonne = { key: string; label: string; align?: "end"; mono?: boolean };
export type Rangee = Record<string, ReactNode> & { id?: string; selected?: boolean };

/** Tableau professionnel, dense si besoin. */
export function Table({
  columns,
  rows = [],
  caption,
  dense,
  loading,
  empty = "Aucune donnée.",
  className,
}: {
  columns: Colonne[];
  rows?: Rangee[];
  caption?: ReactNode;
  dense?: boolean;
  loading?: boolean;
  empty?: string;
  className?: string;
}) {
  return (
    <div className={cx("lf-table-wrap", className)}>
      <table className={cx("lf-table", dense && "lf-table--dense")}>
        {caption && <caption>{caption}</caption>}
        <thead>
          <tr>
            {columns.map((colonne) => (
              <th key={colonne.key} scope="col" className={colonne.align === "end" ? "is-end" : undefined}>
                {colonne.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {loading ? (
            [0, 1, 2].map((i) => (
              <tr key={i} aria-hidden="true">
                {columns.map((colonne) => (
                  <td key={colonne.key}>
                    <span className="lf-skel" />
                  </td>
                ))}
              </tr>
            ))
          ) : rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="lf-table-empty">
                {empty}
              </td>
            </tr>
          ) : (
            rows.map((rangee, i) => (
              <tr key={rangee.id ?? i} className={rangee.selected ? "is-selected" : undefined} aria-selected={rangee.selected || undefined}>
                {columns.map((colonne) => (
                  <td key={colonne.key} className={cx(colonne.align === "end" && "is-end", colonne.mono && "is-mono")}>
                    {rangee[colonne.key]}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
