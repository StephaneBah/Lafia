// États d'une ligne d'ordonnance et d'un cas : pictogramme ou icône, mot et couleur, toujours ensemble.
// Et la posologie, en pictogrammes : quand, combien, avant ou après le repas, combien de jours.

import type { NomIcone } from "./generes/icones";
import type { NomPictogramme } from "./generes/pictogrammes";
import { Icon } from "./Icon";
import { Picto } from "./Picto";
import { cx } from "./svg";

export type Status =
  | "apayer"
  | "paye"
  | "aretirer"
  | "partiel"
  | "retire"
  | "allergie"
  | "urgence"
  | "encours"
  | "termine"
  | "attente"
  | "resultat";

const STATUTS: Record<Status, { ton: string; libelle: string; picto?: NomPictogramme; icone?: NomIcone }> = {
  apayer: { ton: "apayer", picto: "a-payer", libelle: "À payer" },
  paye: { ton: "paye", picto: "paye", libelle: "Payé" },
  aretirer: { ton: "aretirer", picto: "a-retirer", libelle: "À retirer" },
  partiel: { ton: "partiel", picto: "retire-partie", libelle: "Retiré en partie" },
  retire: { ton: "retire", picto: "retire", libelle: "Retiré" },
  allergie: { ton: "danger", picto: "allergie", libelle: "Allergie" },
  urgence: { ton: "danger", picto: "urgence", libelle: "Urgence" },
  encours: { ton: "aretirer", icone: "heartbeat", libelle: "Cas en cours" },
  termine: { ton: "retire", icone: "check", libelle: "Cas terminé" },
  attente: { ton: "apayer", icone: "flask", libelle: "Analyse en attente" },
  resultat: { ton: "paye", icone: "test-tube", libelle: "Résultat disponible" },
};

const TAILLE_DU_PICTO = { citizen: 28, large: 40, pro: 20 } as const;

/** Statut : pictogramme (ou icône) + mot + couleur. La couleur ne porte jamais le sens seule. */
export function StatusBadge({
  status,
  size = "citizen",
  label,
  className,
}: {
  status: Status;
  size?: "citizen" | "large" | "pro";
  label?: string;
  className?: string;
}) {
  const statut = STATUTS[status];
  return (
    <span className={cx("lf-badge", `lf-tone-${statut.ton}`, `lf-badge--${size}`, className)}>
      {statut.picto ? (
        <Picto name={statut.picto} size={TAILLE_DU_PICTO[size]} decorative />
      ) : (
        <Icon name={statut.icone ?? "info"} size={size === "pro" ? 16 : 20} />
      )}
      <span>{label ?? statut.libelle}</span>
    </span>
  );
}

export type Moment = "matin" | "midi" | "soir" | "nuit";
const LIBELLES_DES_MOMENTS: Record<Moment, string> = { matin: "Matin", midi: "Midi", soir: "Soir", nuit: "Nuit" };

export type Posologie = {
  /** Comprimés par prise ; 0,5 pour un demi. */
  count?: number;
  moments?: Moment[];
  meal?: "avant" | "apres";
  days?: number;
  size?: number;
};

/** La posologie en pictogrammes, chacun avec son mot : ce qu'une personne qui ne lit pas doit voir. */
export function Posology({ count, moments = [], meal, days, size = 36 }: Posologie) {
  const demi = count === 0.5;
  return (
    <div className="lf-poso">
      {moments.map((moment) => (
        <span key={moment} className="lf-poso-item">
          <Picto name={moment} size={size} decorative />
          <span className="lf-poso-cap">{LIBELLES_DES_MOMENTS[moment]}</span>
        </span>
      ))}
      {meal && (
        <span className="lf-poso-item">
          <Picto name={meal === "avant" ? "avant-repas" : "apres-repas"} size={size} decorative />
          <span className="lf-poso-cap">{meal === "avant" ? "Avant repas" : "Après repas"}</span>
        </span>
      )}
      {count ? (
        <span className="lf-poso-item">
          <span className="lf-poso-count">
            <Picto name={demi ? "comprime-demi" : "comprime"} size={size} decorative />
            <b aria-hidden="true">{`×${demi ? "½" : count}`}</b>
          </span>
          <span className="lf-poso-cap">{demi ? "½ comprimé" : `${count} ${count > 1 ? "comprimés" : "comprimé"}`}</span>
        </span>
      ) : null}
      {days ? (
        <span className="lf-poso-item">
          <span className="lf-poso-count">
            <Picto name="jours" size={size} decorative />
            <b aria-hidden="true">{days}</b>
          </span>
          <span className="lf-poso-cap">{`${days} ${days > 1 ? "jours" : "jour"}`}</span>
        </span>
      ) : null}
    </div>
  );
}
