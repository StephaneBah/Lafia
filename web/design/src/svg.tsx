// Un SVG dont le contenu vient des fichiers de assets/ (src/generes), avec son accessibilité :
// un libellé en fait une image nommée, sinon il est masqué aux lecteurs d'écran.

export function cx(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(" ");
}

export function SvgBrut({
  contenu,
  viewBox,
  largeur,
  hauteur = largeur,
  libelle,
  className,
}: {
  contenu: string;
  viewBox: string;
  largeur?: number;
  hauteur?: number;
  libelle?: string | null;
  className?: string;
}) {
  const accessibilite = libelle
    ? ({ role: "img", "aria-label": libelle } as const)
    : ({ "aria-hidden": true, focusable: false } as const);
  return (
    <svg
      className={className}
      width={largeur}
      height={hauteur}
      viewBox={viewBox}
      xmlns="http://www.w3.org/2000/svg"
      {...accessibilite}
      dangerouslySetInnerHTML={{ __html: contenu }}
    />
  );
}
