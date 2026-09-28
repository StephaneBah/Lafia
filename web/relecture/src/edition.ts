// La Transcription en cours de Relecture, vue comme une suite de volets qu'on corrige, déplace, coupe,
// fusionne ; et le Markdown de l'ADR 0010 qu'elle redevient à chaque enregistrement. Toute lecture du
// Markdown passe par l'analyseur partagé (@lafia/commun/transcription) : rien n'est relu ici à la main.
import {
  lireTranscription,
  titreDeVolet,
  type TypeDeVolet,
  type Volet,
} from "@lafia/commun/transcription";

/** Un volet tel que le relecteur le travaille. */
export type VoletEdite = {
  /** Clé stable pour l'écran : ne change ni au déplacement ni à la correction. */
  cle: string;
  /** Le titre sans « ## », tel qu'il sera écrit : reconstruit par `titreDeVolet` dès qu'on change le volet. */
  titre: string;
  type: TypeDeVolet;
  date: string | null;
  etablissement: string | null;
  pages: number[];
  corps: string;
  /** Sa place dans le brouillon tel qu'il a été ouvert ; `null` pour un volet ajouté. */
  origine: number | null;
  /** Coché « Vérifié contre les pages ». */
  verifie: boolean;
};

export type Brouillon = {
  /** L'en-tête de l'ADR 0010 et ce qui précède le premier volet, gardés tels quels (l'en-tête est recalculé). */
  preambule: string;
  volets: VoletEdite[];
};

export type Meta = Pick<VoletEdite, "type" | "date" | "etablissement" | "pages">;

const IMAGE = /!\[[^\]]*\]\(page:\d+(?:#\d+,\d+,\d+,\d+)?\)/g;
export const FORMAT_DE_DATE = /^\d{4}(-(0[1-9]|1[0-2])(-(0[1-9]|[12]\d|3[01]))?)?$/;

let compteur = 0;
/** Une clé pour un volet né à l'écran (jamais au premier rendu : le serveur et le navigateur la tireraient différemment). */
export function nouvelleCle(): string {
  compteur += 1;
  return `n${Date.now().toString(36)}${compteur}`;
}

/** Le texte d'un volet, tel qu'il s'écrit dans la Transcription. */
export function texteDuVolet(v: Pick<VoletEdite, "titre" | "corps">): string {
  return `## ${v.titre}\n${v.corps}`.trimEnd();
}

/** Le volet vu par le moteur de rendu partagé. */
export function enVolet(v: VoletEdite, rang: number): Volet {
  return { titre: v.titre, type: v.type, date: v.date, etablissement: v.etablissement, pages: v.pages, corps: v.corps, rang };
}

function lignes(markdown: string): string[] {
  return markdown.replace(/\r\n/g, "\n").split("\n");
}

/** Ce qui précède le premier volet : l'en-tête et, rarement, quelques lignes libres. */
function preambuleDe(markdown: string): string {
  const toutes = lignes(markdown);
  let debut = 0;
  if (toutes[0]?.trim() === "---") {
    const fin = toutes.findIndex((l, i) => i > 0 && l.trim() === "---");
    if (fin > 0) debut = fin + 1;
  }
  const premier = toutes.findIndex((l, i) => i >= debut && l.startsWith("## "));
  return (premier < 0 ? toutes : toutes.slice(0, premier)).join("\n").trim();
}

/** Le brouillon ouvert : chaque volet se souvient de sa place d'origine. */
export function depuisMarkdown(markdown: string, pagesDuDocument: number): Brouillon {
  const lue = lireTranscription(markdown, pagesDuDocument);
  return {
    preambule: preambuleDe(markdown),
    volets: lue.volets.map((v, i) => ({
      cle: `o${i}`,
      titre: v.titre,
      type: v.type,
      date: v.date,
      etablissement: v.etablissement,
      pages: v.pages,
      corps: v.corps,
      origine: i,
      verifie: false,
    })),
  };
}

/**
 * Le Markdown relu dans la vue brute, redevenu des volets : chacun reprend, s'il le retrouve, le volet
 * dont il vient (même texte d'abord, même place ensuite), pour garder son origine et sa coche.
 */
export function depuisLeBrut(markdown: string, pagesDuDocument: number, avant: VoletEdite[]): Brouillon {
  const lu = depuisMarkdown(markdown, pagesDuDocument);
  const pris = new Set<string>();
  const volets = lu.volets.map((v, i) => {
    const meme = avant.find((a) => !pris.has(a.cle) && texteDuVolet(a) === texteDuVolet(v));
    if (meme) {
      pris.add(meme.cle);
      return { ...v, cle: meme.cle, origine: meme.origine, verifie: meme.verifie };
    }
    const place = avant[i];
    if (place && !pris.has(place.cle)) {
      pris.add(place.cle);
      return { ...v, cle: place.cle, origine: place.origine, verifie: false };
    }
    return { ...v, cle: nouvelleCle(), origine: null };
  });
  return { preambule: lu.preambule, volets };
}

/** L'en-tête de l'ADR 0010, recalculé des volets : les établissements dans l'ordre où ils paraissent, la période. */
function avecEntete(preambule: string, volets: VoletEdite[]): string {
  const etablissements = [...new Set(volets.map((v) => v.etablissement).filter((e): e is string => Boolean(e)))];
  const annees = volets.map((v) => v.date?.slice(0, 4)).filter((a): a is string => Boolean(a)).sort();
  const periode = annees.length ? (annees[0] === annees[annees.length - 1] ? annees[0] : `${annees[0]}-${annees[annees.length - 1]}`) : null;

  const toutes = lignes(preambule);
  let cles: string[] = [];
  let reste = toutes;
  if (toutes[0]?.trim() === "---") {
    const fin = toutes.findIndex((l, i) => i > 0 && l.trim() === "---");
    if (fin > 0) {
      cles = toutes.slice(1, fin).filter((l) => !/^\s*(etablissements|periode)\s*:/.test(l));
      reste = toutes.slice(fin + 1);
    }
  }
  const entete = [
    ...(etablissements.length ? [`etablissements: ${etablissements.join("; ")}`] : []),
    ...(periode ? [`periode: ${periode}`] : []),
    ...cles,
  ];
  const libre = reste.join("\n").trim();
  return [entete.length ? ["---", ...entete, "---"].join("\n") : "", libre].filter(Boolean).join("\n\n");
}

/** Le Markdown du brouillon, prêt à enregistrer. */
export function versMarkdown(brouillon: Brouillon): string {
  const tete = avecEntete(brouillon.preambule, brouillon.volets);
  const corps = brouillon.volets.map(texteDuVolet).join("\n\n");
  return `${[tete, corps].filter(Boolean).join("\n\n")}\n`;
}

/** Un volet dont on change le type, la date, l'établissement ou les pages : son titre est reconstruit. */
export function avecMeta(v: VoletEdite, meta: Partial<Meta>): VoletEdite {
  const suivant = { ...v, ...meta };
  return { ...suivant, titre: titreDeVolet(suivant).slice(3) };
}

/** Ce que l'ADR 0010 reproche à ce volet seul, sans numéro de ligne. */
export function erreursDuVolet(v: VoletEdite, pagesDuDocument: number): string[] {
  return lireTranscription(texteDuVolet(v), pagesDuDocument).erreurs.map((e) => e.replace(/^ligne \d+ : /, ""));
}

/** Les pages écrites « 3-4, 6 », lues par l'analyseur partagé ; `null` quand elles ne se lisent pas. */
export function lirePages(texte: string): number[] | null {
  const propre = texte.trim();
  if (!propre) return [];
  if (!/^[0-9 ,\-–]+$/.test(propre)) return null;
  const pages = lireTranscription(`## autre · ? · ? · p. ${propre}`).volets[0]?.pages ?? [];
  return pages.length ? [...pages].sort((a, b) => a - b) : null;
}

export function pagesEnTexte(pages: number[]): string {
  return titreDeVolet({ type: "autre", date: null, etablissement: null, pages }).split("p. ")[1].replace("?", "");
}

/** Un volet vide, prêt à écrire, sur les pages données. */
export function voletVide(pages: number[]): VoletEdite {
  return avecMeta(
    { cle: nouvelleCle(), titre: "", type: "consultation", date: null, etablissement: null, pages, corps: "", origine: null, verifie: false },
    {},
  );
}

/** Coupé au curseur : le début reste, la suite devient un volet neuf, sur les mêmes pages. Les deux sont à revérifier. */
export function couper(volets: VoletEdite[], index: number, position: number): VoletEdite[] {
  const v = volets[index];
  const debut = v.corps.slice(0, position).trimEnd();
  const fin = v.corps.slice(position).trim();
  const suite: VoletEdite = { ...v, cle: nouvelleCle(), corps: fin, origine: null, verifie: false };
  return [...volets.slice(0, index), { ...v, corps: debut, verifie: false }, suite, ...volets.slice(index + 1)];
}

/** Le volet et le suivant en un seul : le texte bout à bout, les pages réunies, le reste du premier. */
export function fusionner(volets: VoletEdite[], index: number): VoletEdite[] {
  const [a, b] = [volets[index], volets[index + 1]];
  if (!b) return volets;
  const pages = [...new Set([...a.pages, ...b.pages])].sort((x, y) => x - y);
  const corps = [a.corps, b.corps].filter((c) => c.trim()).join("\n\n");
  const memesPages = pages.length === a.pages.length;
  const fusion = memesPages ? { ...a, corps, verifie: false } : { ...avecMeta(a, { pages }), corps, verifie: false };
  return [...volets.slice(0, index), fusion, ...volets.slice(index + 2)];
}

export function deplacer(volets: VoletEdite[], index: number, vers: number): VoletEdite[] {
  if (vers < 0 || vers >= volets.length) return volets;
  const copie = [...volets];
  const [v] = copie.splice(index, 1);
  copie.splice(vers, 0, v);
  return copie;
}

/** Une photo de page à écrire dans un volet : la page entière, ou une zone en pour-mille. */
export function imageDePage(page: number, legende: string, zone?: [number, number, number, number]): string {
  const propre = legende.replace(/[[\]\n]/g, " ").trim();
  return `![${propre}](page:${page}${zone ? `#${zone.map((n) => Math.round(n)).join(",")}` : ""})`;
}

export function inserer(corps: string, position: number, morceau: string): string {
  // Une ligne vide de part et d'autre : la photo reste un bloc à elle, jamais collée à un tableau ou une liste.
  const avant = corps.slice(0, position).replace(/\n*$/, "");
  const apres = corps.slice(position).replace(/^\n*/, "");
  return `${avant}${avant ? "\n\n" : ""}${morceau}${apres ? "\n\n" : ""}${apres}`;
}

function photos(texte: string): number {
  return texte.match(IMAGE)?.length ?? 0;
}

/** Ce qui a changé depuis le brouillon ouvert. */
export type Changements = { ajoutes: number; supprimes: number; modifies: number; deplaces: number; photos: number };

/** La plus longue suite croissante : les volets restés en ordre ; les autres ont été déplacés. */
function enOrdre(suite: number[]): number {
  const fins: number[] = [];
  for (const x of suite) {
    let [bas, haut] = [0, fins.length];
    while (bas < haut) {
      const milieu = (bas + haut) >> 1;
      if (fins[milieu] < x) bas = milieu + 1;
      else haut = milieu;
    }
    fins[bas] = x;
  }
  return fins.length;
}

export function changements(depart: string[], volets: VoletEdite[]): Changements {
  const origines = volets.map((v) => v.origine).filter((o): o is number => o !== null);
  const photosAvant = depart.reduce((n, t) => n + photos(t), 0);
  const photosApres = volets.reduce((n, v) => n + photos(v.corps), 0);
  return {
    ajoutes: volets.filter((v) => v.origine === null).length,
    supprimes: depart.length - new Set(origines).size,
    modifies: volets.filter((v) => v.origine !== null && texteDuVolet(v) !== depart[v.origine]).length,
    deplaces: origines.length - enOrdre(origines),
    photos: Math.max(0, photosApres - photosAvant),
  };
}

function compte(n: number, singulier: string, plurielle: string): string {
  return `${n} ${n > 1 ? plurielle : singulier}`;
}

/** Les changements en une phrase : la proposition de résumé, que le relecteur reprend à sa main. */
export function resumeSuggere(c: Changements): string {
  const parties = [
    c.modifies && compte(c.modifies, "volet corrigé", "volets corrigés"),
    c.ajoutes && compte(c.ajoutes, "volet ajouté", "volets ajoutés"),
    c.supprimes && compte(c.supprimes, "volet supprimé", "volets supprimés"),
    c.deplaces && compte(c.deplaces, "volet remis en ordre", "volets remis en ordre"),
    c.photos && compte(c.photos, "photo de page ajoutée", "photos de page ajoutées"),
  ].filter(Boolean);
  if (!parties.length) return "Relu contre les pages : la lecture de la machine était juste, rien à corriger.";
  return `Relu contre les pages : ${parties.join(", ")}.`;
}

/** Une empreinte courte d'un volet : la coche survit au rechargement tant que le volet n'a pas changé. */
export function empreinte(v: Pick<VoletEdite, "titre" | "corps">): string {
  const texte = texteDuVolet(v);
  let h = 5381;
  for (let i = 0; i < texte.length; i++) h = ((h << 5) + h + texte.charCodeAt(i)) | 0;
  return `${texte.length.toString(36)}-${(h >>> 0).toString(36)}`;
}

// ---- Pour aller vite ----

const MOIS = ["janvier", "fevrier", "mars", "avril", "mai", "juin", "juillet", "aout", "septembre", "octobre", "novembre", "decembre"];

function sansAccents(texte: string): string {
  return texte.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

function deuxChiffres(n: number): string {
  return String(n).padStart(2, "0");
}

/**
 * Une date telle qu'on la lit sur le papier, dans le format de l'ADR 0010 : « 14/03/2019 », « 14-3-2019 »,
 * « 03/2019 », « mars 2019 », « 14 mars 2019 », « 2019 » ; `null` quand elle ne se lit pas.
 */
export function normaliserDate(texte: string): string | null {
  const t = sansAccents(texte.trim()).replace(/\s+/g, " ").replace(/^le /, "").replace(/(\d)er\b/, "$1");
  // Un jour qui existe dans son mois : le 31/02 n'est pas une lecture, c'est une erreur de saisie.
  const valide = (a: number, m?: number, j?: number) =>
    a >= 1900 &&
    a <= 2100 &&
    (m === undefined || (m >= 1 && m <= 12)) &&
    (j === undefined || (m !== undefined && j >= 1 && j <= new Date(Date.UTC(a, m, 0)).getUTCDate()));
  let m = /^(\d{4})(?:-(\d{1,2})(?:-(\d{1,2}))?)?$/.exec(t);
  if (m && valide(+m[1], m[2] ? +m[2] : undefined, m[3] ? +m[3] : undefined)) {
    return [m[1], ...(m[2] ? [deuxChiffres(+m[2])] : []), ...(m[3] ? [deuxChiffres(+m[3])] : [])].join("-");
  }
  m = /^(\d{1,2})[/.\- ](\d{1,2})[/.\- ](\d{4})$/.exec(t);
  if (m && valide(+m[3], +m[2], +m[1])) return `${m[3]}-${deuxChiffres(+m[2])}-${deuxChiffres(+m[1])}`;
  m = /^(\d{1,2})[/.\- ](\d{4})$/.exec(t);
  if (m && valide(+m[2], +m[1])) return `${m[2]}-${deuxChiffres(+m[1])}`;
  m = /^(?:(\d{1,2}) )?([a-z]+)\.? (\d{4})$/.exec(t);
  if (m) {
    // « jui » peut être juin ou juillet : un mois abrégé ne se lit que s'il n'en désigne qu'un.
    const candidats = m[2].length >= 3 ? MOIS.filter((nom) => nom.startsWith(m![2])) : [];
    const mois = candidats.length === 1 ? MOIS.indexOf(candidats[0]) + 1 : 0;
    if (mois && valide(+m[3], mois, m[1] ? +m[1] : undefined)) {
      return m[1] ? `${m[3]}-${deuxChiffres(mois)}-${deuxChiffres(+m[1])}` : `${m[3]}-${deuxChiffres(mois)}`;
    }
  }
  return null;
}

/** Pourquoi un volet mérite qu'on le regarde de près : la machine y a buté, ou il manque quelque chose. */
export function aRegarder(v: VoletEdite, erreurs: string[]): string[] {
  const raisons: string[] = [];
  if (v.type === "illisible") raisons.push("passage illisible");
  if (erreurs.length) raisons.push("hors format");
  if (!v.corps.trim()) raisons.push("texte vide");
  if (/\[\?\]|\?\?|illisible/i.test(v.corps) && v.type !== "illisible") raisons.push("lecture incertaine");
  if (!v.pages.length) raisons.push("aucune page");
  return raisons;
}

/** Ce qui a changé dans un volet, ligne à ligne : retirées, ajoutées. */
export function lignesChangees(avant: string, apres: string): { retirees: string[]; ajoutees: string[] } {
  const a = avant.split("\n");
  const b = apres.split("\n");
  const restantes = [...b];
  const retirees: string[] = [];
  for (const ligne of a) {
    const i = restantes.indexOf(ligne);
    if (i >= 0) restantes.splice(i, 1);
    else retirees.push(ligne);
  }
  return { retirees: retirees.filter((l) => l.trim()), ajoutees: restantes.filter((l) => l.trim()) };
}

export type ChangementDeVolet =
  | { genre: "ajoute"; rang: number; texte: string }
  | { genre: "modifie"; rang: number; origine: number; retirees: string[]; ajoutees: string[] }
  | { genre: "supprime"; origine: number; texte: string };

/** Le détail des changements depuis l'ouverture, volet par volet, pour la fenêtre de confirmation. */
export function detailDesChangements(depart: string[], volets: VoletEdite[]): ChangementDeVolet[] {
  const presents = new Set(volets.map((v) => v.origine));
  const detail: ChangementDeVolet[] = [];
  volets.forEach((v, rang) => {
    const texte = texteDuVolet(v);
    if (v.origine === null) detail.push({ genre: "ajoute", rang, texte });
    else if (texte !== depart[v.origine]) detail.push({ genre: "modifie", rang, origine: v.origine, ...lignesChangees(depart[v.origine], texte) });
  });
  depart.forEach((texte, origine) => {
    if (!presents.has(origine)) detail.push({ genre: "supprime", origine, texte });
  });
  return detail;
}
