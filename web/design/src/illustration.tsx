// Les illustrations de la charte, insérées en SVG dans la page : aucune requête de plus, et le fil
// (`.lf-fil`) s'anime en CSS. Point d'entrée séparé (`@lafia/design/illustration`), à n'importer que
// dans des composants serveur : les scènes restent hors du JavaScript envoyé au navigateur.

import { ILLUSTRATIONS, type NomIllustration } from "./generes/illustrations";
import { SvgBrut } from "./svg";

export type { NomIllustration };

/**
 * Une illustration. Nommée par son titre quand elle porte le sens ; `decorative` quand le texte voisin
 * le dit déjà.
 */
export function Illustration({
  name,
  label,
  decorative = false,
  className,
}: {
  name: NomIllustration;
  label?: string;
  decorative?: boolean;
  className?: string;
}) {
  const { viewBox, titre, contenu } = ILLUSTRATIONS[name];
  return <SvgBrut contenu={contenu} viewBox={viewBox} libelle={decorative ? null : (label ?? titre)} className={className} />;
}
