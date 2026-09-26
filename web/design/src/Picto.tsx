import { LIBELLES_DES_PICTOGRAMMES, PICTOGRAMMES, type NomPictogramme } from "./generes/pictogrammes";
import { SvgBrut, cx } from "./svg";

/**
 * Pictogramme Lafia (grille 48) : seulement pour ce qu'aucune icône ne dit sans ambiguïté, posologie,
 * états d'ordonnance, allergie, urgence, qui a consulté le dossier. Nommé par son titre, sauf
 * `decorative` quand un mot voisin dit déjà la même chose.
 */
export function Picto({
  name,
  size = 48,
  label,
  decorative = false,
  className,
}: {
  name: NomPictogramme;
  size?: number;
  label?: string;
  decorative?: boolean;
  className?: string;
}) {
  return (
    <SvgBrut
      contenu={PICTOGRAMMES[name]}
      viewBox="0 0 48 48"
      largeur={size}
      libelle={decorative ? null : (label ?? LIBELLES_DES_PICTOGRAMMES[name])}
      className={cx("lf-picto", className)}
    />
  );
}
