import { formatDate } from "@lafia/design";

import type { PointDeMesure } from "../lib/types";

const L = 560;
const H = 200;
const MARGE = { haut: 16, droite: 16, bas: 32, gauche: 40 };
const SEUIL = 38;

const virgule = (n: number) => n.toFixed(1).replace(".", ",");

/**
 * La courbe de température d'un patient, en SVG dans la page : ligne, points, seuil de fièvre à 38 °C
 * tracé en pointillé et nommé en toutes lettres. Chaque point est lisible au clavier et au lecteur
 * d'écran, et un tableau des valeurs double la courbe pour qui ne la voit pas.
 */
export function CourbeDeTemperature({ serie }: { serie: PointDeMesure[] }) {
  const points = serie
    .map((p) => ({ date: p.date, valeur: Number(String(p.valeur).replace(",", ".")) }))
    .filter((p) => Number.isFinite(p.valeur));
  if (points.length === 0) return <div className="sn-vide">Aucune température mesurée.</div>;

  const valeurs = points.map((p) => p.valeur);
  const min = Math.floor(Math.min(36, ...valeurs) * 2) / 2;
  const max = Math.ceil(Math.max(39.5, ...valeurs) * 2) / 2;
  const largeur = L - MARGE.gauche - MARGE.droite;
  const hauteur = H - MARGE.haut - MARGE.bas;
  const x = (i: number) => MARGE.gauche + (points.length === 1 ? largeur / 2 : (i * largeur) / (points.length - 1));
  const y = (v: number) => MARGE.haut + ((max - v) * hauteur) / (max - min);
  const trace = points.map((p, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(p.valeur).toFixed(1)}`).join(" ");
  const graduations: number[] = [];
  for (let v = Math.ceil(min); v <= max; v += 1) graduations.push(v);
  const derniere = points[points.length - 1];
  const fievres = points.filter((p) => p.valeur >= SEUIL).length;

  return (
    <figure className="sn-courbe">
      <svg
        viewBox={`0 0 ${L} ${H}`}
        role="img"
        aria-labelledby="courbe-titre courbe-resume"
        className="sn-courbe-svg"
      >
        <title id="courbe-titre">Température au fil des visites</title>
        <desc id="courbe-resume">
          {`${points.length} mesure${points.length > 1 ? "s" : ""}, la dernière à ${virgule(derniere.valeur)} °C ; ${fievres} au-dessus du seuil de fièvre de 38 °C.`}
        </desc>
        {graduations.map((v) => (
          <g key={v} aria-hidden="true">
            <line x1={MARGE.gauche} x2={L - MARGE.droite} y1={y(v)} y2={y(v)} className="sn-courbe-grille" />
            <text x={MARGE.gauche - 8} y={y(v) + 4} textAnchor="end" className="sn-courbe-axe">
              {v}
            </text>
          </g>
        ))}
        <g aria-hidden="true">
          <line x1={MARGE.gauche} x2={L - MARGE.droite} y1={y(SEUIL)} y2={y(SEUIL)} className="sn-courbe-seuil" />
          <text x={L - MARGE.droite} y={y(SEUIL) - 6} textAnchor="end" className="sn-courbe-seuil-texte">
            Fièvre 38 °C
          </text>
        </g>
        <path d={trace} className="sn-courbe-ligne" aria-hidden="true" />
        {points.map((p, i) => {
          const fievre = p.valeur >= SEUIL;
          return (
            <g key={i} tabIndex={0} role="img" aria-label={`${formatDate(p.date)} : ${virgule(p.valeur)} °C${fievre ? ", fièvre" : ""}`} className="sn-courbe-point">
              <title>{`${formatDate(p.date)} · ${virgule(p.valeur)} °C`}</title>
              {fievre ? (
                <rect x={x(i) - 6} y={y(p.valeur) - 6} width={12} height={12} className="sn-courbe-fievre" />
              ) : (
                <circle cx={x(i)} cy={y(p.valeur)} r={6} className="sn-courbe-rond" />
              )}
            </g>
          );
        })}
        {points.length <= 8 &&
          points.map((p, i) => (
            <text key={`d${i}`} x={x(i)} y={H - 10} textAnchor="middle" className="sn-courbe-axe" aria-hidden="true">
              {formatDate(p.date).slice(0, 5)}
            </text>
          ))}
      </svg>
      <figcaption className="sn-meta">
        Carré : fièvre, à 38 °C ou plus. Rond : sous le seuil. Tabulez sur un point pour sa valeur.
      </figcaption>
      <details className="sn-details">
        <summary>Voir les valeurs</summary>
        <table className="sn-table">
          <thead>
            <tr>
              <th scope="col">Date</th>
              <th scope="col">Température</th>
            </tr>
          </thead>
          <tbody>
            {points.map((p, i) => (
              <tr key={i}>
                <td>{formatDate(p.date)}</td>
                <td>{`${virgule(p.valeur)} °C${p.valeur >= SEUIL ? " · fièvre" : ""}`}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}
