import { LOGO } from "./generes/logo";
import { cx } from "./svg";

const [, , LARGEUR_VB, HAUTEUR_VB] = LOGO.viewBox.split(" ").map(Number);

/**
 * Le mot « Lafia » et son point, la personne : `royal` sur clair, `blanc` sur royal, denim ou
 * ardoise, `noir` sur le reçu. `animate` : le point se pose en dernier.
 */
export function Logo({
  tone = "royal",
  height = 32,
  href,
  linkLabel = "Lafia, retour au site",
  animate = false,
}: {
  tone?: "royal" | "blanc" | "noir";
  height?: number;
  href?: string;
  linkLabel?: string;
  animate?: boolean;
}) {
  const svg = (
    <svg
      className={cx("lf-logo", `lf-logo--${tone}`, animate && "lf-logo--animate")}
      width={Math.round((height * LARGEUR_VB) / HAUTEUR_VB)}
      height={height}
      viewBox={LOGO.viewBox}
      role="img"
      aria-label="Lafia"
    >
      <path className="lf-logo-word" d={LOGO.mot} />
      <circle className="lf-logo-dot" cx={LOGO.point.cx} cy={LOGO.point.cy} r={LOGO.point.r} />
    </svg>
  );
  if (!href) return svg;
  return (
    <a className="lf-logo-link" href={href} aria-label={linkLabel}>
      {svg}
    </a>
  );
}
