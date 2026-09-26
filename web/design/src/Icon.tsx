import { ICONES, ICONES_DUOTONE, type NomIcone } from "./generes/icones";
import { SvgBrut, cx } from "./svg";

/**
 * Icône Phosphor : `bold` dans l'interface, `duotone` à côté des illustrations. Toujours avec un mot
 * visible ; sinon (fermer, retour, menu) avec un `label`.
 */
export function Icon({
  name,
  size = 24,
  duotone = false,
  label,
  className,
}: {
  name: NomIcone;
  size?: number;
  duotone?: boolean;
  label?: string;
  className?: string;
}) {
  const contenu = (duotone && ICONES_DUOTONE[name]) || ICONES[name];
  return <SvgBrut contenu={contenu} viewBox="0 0 256 256" largeur={size} libelle={label} className={cx("lf-icon", className)} />;
}
