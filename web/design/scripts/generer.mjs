// Génère src/generes/*.ts depuis les SVG de assets/ : les fichiers SVG restent la source, les
// composants lisent ces modules. À relancer après tout changement dans assets/ :
//   npm run generer --workspace @lafia/design

import { readdirSync, readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { basename, join } from "node:path";

const racine = join(import.meta.dirname, "..");
const assets = join(racine, "assets");
const sortie = join(racine, "src", "generes");
mkdirSync(sortie, { recursive: true });

/** Le viewBox, le titre et le contenu d'un fichier SVG, sans sa balise racine ni son <title>. */
function lire(fichier) {
  const svg = readFileSync(fichier, "utf-8").trim();
  const racineSvg = svg.match(/^<svg\b([^>]*)>/);
  if (!racineSvg) throw new Error(`${fichier} : pas de balise <svg> en tête`);
  const viewBox = racineSvg[1].match(/viewBox="([^"]+)"/)?.[1];
  if (!viewBox) throw new Error(`${fichier} : pas de viewBox`);
  const titre = svg.match(/<title>([^<]*)<\/title>/)?.[1] ?? racineSvg[1].match(/aria-label="([^"]+)"/)?.[1] ?? "";
  const contenu = svg
    .slice(racineSvg[0].length, svg.lastIndexOf("</svg>"))
    .replace(/<title>[^<]*<\/title>/, "")
    .trim();
  return { viewBox, titre, contenu };
}

function fichiers(dossier) {
  return readdirSync(join(assets, dossier))
    .filter((nom) => nom.endsWith(".svg"))
    .sort()
    .map((nom) => ({ nom: basename(nom, ".svg"), chemin: join(assets, dossier, nom) }));
}

function ecrire(nom, source) {
  const entete = "// Généré par scripts/generer.mjs depuis assets/ : ne pas modifier à la main.\n\n";
  writeFileSync(join(sortie, nom), entete + source);
}

const union = (noms) => noms.map((n) => JSON.stringify(n)).join(" | ");

// Icônes Phosphor : `nom-bold.svg` et `nom-duotone.svg`, viewBox 256, couleur héritée du texte.
const icones = {};
const duotones = {};
for (const { nom, chemin } of fichiers("Icones")) {
  const { contenu } = lire(chemin);
  if (nom.endsWith("-bold")) icones[nom.slice(0, -5)] = contenu;
  else if (nom.endsWith("-duotone")) duotones[nom.slice(0, -8)] = contenu;
}
ecrire(
  "icones.ts",
  `export type NomIcone = ${union(Object.keys(icones))};\n\n` +
    `export const ICONES: Record<NomIcone, string> = ${JSON.stringify(icones, null, 2)};\n\n` +
    `export const ICONES_DUOTONE: Partial<Record<NomIcone, string>> = ${JSON.stringify(duotones, null, 2)};\n`,
);

// Pictogrammes Lafia : grille 48, encres fixes.
const pictogrammes = {};
const libelles = {};
for (const { nom, chemin } of fichiers("Pictogrammes")) {
  const { contenu, titre } = lire(chemin);
  pictogrammes[nom] = contenu;
  libelles[nom] = titre;
}
ecrire(
  "pictogrammes.ts",
  `export type NomPictogramme = ${union(Object.keys(pictogrammes))};\n\n` +
    `export const PICTOGRAMMES: Record<NomPictogramme, string> = ${JSON.stringify(pictogrammes, null, 2)};\n\n` +
    `/** L'alternative textuelle de chaque pictogramme, son <title>. */\n` +
    `export const LIBELLES_DES_PICTOGRAMMES: Record<NomPictogramme, string> = ${JSON.stringify(libelles, null, 2)};\n`,
);

// Logo : le mot (un chemin) et le point du « i » (un cercle), que les composants colorent par tonalité.
const logo = lire(join(assets, "Logo", "lafia-logo.svg"));
const mot = logo.contenu.match(/<path\b[^>]*\sd="([^"]+)"/)?.[1];
const point = logo.contenu.match(/<circle\b[^>]*\scx="([^"]+)"[^>]*\scy="([^"]+)"[^>]*\sr="([^"]+)"/);
if (!mot || !point) throw new Error("lafia-logo.svg : le mot ou le point est introuvable");
ecrire(
  "logo.ts",
  `export const LOGO = ${JSON.stringify(
    { viewBox: logo.viewBox, mot, point: { cx: Number(point[1]), cy: Number(point[2]), r: Number(point[3]) } },
    null,
    2,
  )} as const;\n`,
);

// Illustrations : scènes complètes, chacune avec son alternative textuelle.
const illustrations = {};
for (const { nom, chemin } of fichiers("Illustrations")) {
  illustrations[nom] = lire(chemin);
}
ecrire(
  "illustrations.ts",
  `export type NomIllustration = ${union(Object.keys(illustrations))};\n\n` +
    `export const ILLUSTRATIONS: Record<NomIllustration, { viewBox: string; titre: string; contenu: string }> = ${JSON.stringify(illustrations, null, 2)};\n`,
);

console.log(
  `icônes ${Object.keys(icones).length} (+${Object.keys(duotones).length} duotone), ` +
    `pictogrammes ${Object.keys(pictogrammes).length}, illustrations ${Object.keys(illustrations).length}`,
);
