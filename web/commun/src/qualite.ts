// La capture rigoureuse (F6.5) : chaque page photographiée ou choisie est jugée dans le navigateur, avant
// d'être gardée. Le citoyen ne vient qu'une fois : une page floue, sombre, coupée ou éblouie se reprend
// au guichet en dix secondes, jamais après. Une page qui échoue ne se garde pas, sauf un papier abîmé
// en lui-même, que l'agent déclare et note sur le Document.
//
// La mesure se fait sur une copie en gris réduite à 800 px sur son grand côté (luma Rec. 601) :
//
// | Mesure     | Calcul                                                   | Seuil                         |
// |------------|----------------------------------------------------------|-------------------------------|
// | Résolution | grand côté de l'image d'origine, avant compression        | au moins 1200 px              |
// | Luminosité | moyenne des gris (0 à 255)                                | au moins 70                   |
// | Contraste  | écart type des gris                                       | au moins 20                   |
// | Netteté    | variance du laplacien (noyau à 4 voisins)                 | au moins 100                  |
// | Reflet     | part des pixels à 250 ou plus                             | au plus 2 % de l'image        |
// | Cadrage    | un bord de l'image où le papier continue, encre comprise  | aucun des quatre bords        |
//
// Pourquoi ces seuils. Une page de 1200 px de grand côté garde une écriture manuscrite de 2 à 3 px de
// trait, le minimum pour qu'un relecteur la déchiffre ; au-dessous, la compression à 1600 px n'y
// ajoute rien. Une photo de papier bien éclairée a une moyenne de 150 à 220 : sous 70, l'encre et le
// papier se confondent dans le bruit. Un papier écrit, même peu, a un écart type de 35 et plus ; sous
// 20, c'est un voile, un contre-jour ou une page vide. À 800 px, une page d'écriture nette donne une
// variance du laplacien de l'ordre du millier (4 000 pour la page dense du test) ; un flou de 3 px la
// fait tomber vers 600, de 5 px vers 140, de 7 px vers 60, où les lettres ne se distinguent plus : 100
// garde la page un peu douce et refuse celle qui ne se lit plus. Une page presque vide mesure bas aussi :
// elle se reprend, ou se garde comme papier abîmé. Un reflet est une tache où le capteur sature :
// au-delà de 2 % de l'image, il efface des lignes. Un scan au fond parfaitement blanc sature partout ;
// quand le papier lui-même est à 245 ou plus, il n'y a pas de reflet à chercher.
//
// Le cadrage. Ce qui compte est que rien du papier ne manque : un bord de l'image est « coupé » quand
// sa ligne la plus extérieure est du papier (sa médiane est proche du blanc du papier) et que ses quatre
// lignes extérieures portent de l'encre en traits courts (au moins 1 % du bord, en trois traits au
// moins). Un fond sombre, une table, ou l'angle d'une page penchée donnent de longues plages sombres,
// pas des traits : ils ne comptent pas. Un scan dont les marges sont blanches jusqu'au bord passe : il ne perd rien.
//
// Ces seuils sont un premier réglage, fait sur des images de synthèse (test/qualite.test.ts) ; ils se
// règlent sur de vraies photos du guichet en changeant les constantes ci-dessous, rien d'autre.
//
// Les fonctions de mesure et de jugement sont pures, sur des tableaux de pixels ; seules
// `verifierImage`, `verifierFichier` et `luminositeDuFlux` touchent au navigateur (canvas).

export const COTE_MIN = 1200;
export const COTE_D_ANALYSE = 800;
export const LUMINOSITE_MIN = 70;
export const CONTRASTE_MIN = 20;
export const NETTETE_MIN = 100;
export const SATURE = 250;
export const REFLET_MAX = 0.02;
/** Un papier qui atteint ce blanc est un scan ou une page uniformément claire : pas de reflet à y chercher. */
export const PAPIER_SATURE = 245;
/** Les lignes extérieures lues pour savoir si le papier continue au-delà d'un bord. */
export const LIGNES_DE_BORD = 4;
/** Au-dessous du blanc du papier, de combien un pixel est de l'encre, et de combien une ligne reste du papier. */
export const ECART_D_ENCRE = 70;
export const ECART_DE_PAPIER = 40;
export const ENCRE_AU_BORD_MIN = 0.01;
export const TRAITS_AU_BORD_MIN = 3;

export type CodeDeProbleme = "resolution" | "coupee" | "sombre" | "contraste" | "flou" | "reflet";
export type Probleme = { code: CodeDeProbleme; message: string };
export type Cote = "haut" | "bas" | "gauche" | "droite";

export type Mesures = {
  luminosite: number;
  contraste: number;
  nettete: number;
  reflet: number;
  bordsCoupes: Cote[];
};

export type Verdict = { ok: boolean; problemes: Probleme[]; mesures?: Mesures };

/** Une image en niveaux de gris, de 0 (noir) à 255 (blanc), ligne par ligne. */
export type Gris = { largeur: number; hauteur: number; valeurs: Float32Array };

export const MESSAGES: Record<CodeDeProbleme, string> = {
  resolution: `Image trop petite : rapprochez-vous de la page, ou choisissez une photo d'au moins ${COTE_MIN} pixels de côté`,
  coupee: "Page coupée : reculez pour voir les quatre bords",
  sombre: "Trop sombre : rapprochez-vous de la lumière",
  contraste: "Trop peu de contraste : éclairez la page de face, sans ombre ni contre-jour",
  flou: "Photo floue : tenez l'appareil immobile et laissez-le faire la mise au point",
  reflet: "Reflet : inclinez légèrement la page",
};

function probleme(code: CodeDeProbleme): Probleme {
  return { code, message: MESSAGES[code] };
}

/** Des pixels RGBA (ceux d'un canvas) en gris, par la luma Rec. 601. */
export function enGris(rgba: ArrayLike<number>, largeur: number, hauteur: number): Gris {
  const valeurs = new Float32Array(largeur * hauteur);
  for (let i = 0; i < valeurs.length; i += 1) {
    valeurs[i] = 0.299 * rgba[i * 4] + 0.587 * rgba[i * 4 + 1] + 0.114 * rgba[i * 4 + 2];
  }
  return { largeur, hauteur, valeurs };
}

function moyenneEtEcartType(valeurs: ArrayLike<number>): [number, number] {
  let somme = 0;
  let carres = 0;
  for (let i = 0; i < valeurs.length; i += 1) {
    somme += valeurs[i];
    carres += valeurs[i] * valeurs[i];
  }
  const n = Math.max(1, valeurs.length);
  const moyenne = somme / n;
  return [moyenne, Math.sqrt(Math.max(0, carres / n - moyenne * moyenne))];
}

/** Variance du laplacien à 4 voisins sur l'intérieur de l'image : haute quand les traits sont nets. */
export function varianceDuLaplacien({ largeur, hauteur, valeurs }: Gris): number {
  if (largeur < 3 || hauteur < 3) return 0;
  let somme = 0;
  let carres = 0;
  let n = 0;
  for (let y = 1; y < hauteur - 1; y += 1) {
    for (let x = 1; x < largeur - 1; x += 1) {
      const i = y * largeur + x;
      const l = valeurs[i - 1] + valeurs[i + 1] + valeurs[i - largeur] + valeurs[i + largeur] - 4 * valeurs[i];
      somme += l;
      carres += l * l;
      n += 1;
    }
  }
  const moyenne = somme / n;
  return carres / n - moyenne * moyenne;
}

/** La valeur sous laquelle tombe la part `p` des pixels (0 à 1), à l'unité de gris près. */
export function centile(valeurs: ArrayLike<number>, p: number): number {
  const histogramme = new Uint32Array(256);
  for (let i = 0; i < valeurs.length; i += 1) histogramme[Math.min(255, Math.max(0, Math.round(valeurs[i])))] += 1;
  const rang = p * valeurs.length;
  let cumul = 0;
  for (let v = 0; v < 256; v += 1) {
    cumul += histogramme[v];
    if (cumul >= rang) return v;
  }
  return 255;
}

function ligneDeBord(gris: Gris, cote: Cote, rang: number): Float32Array {
  const { largeur, hauteur, valeurs } = gris;
  if (cote === "haut" || cote === "bas") {
    const y = cote === "haut" ? rang : hauteur - 1 - rang;
    return valeurs.slice(y * largeur, (y + 1) * largeur);
  }
  const x = cote === "gauche" ? rang : largeur - 1 - rang;
  const colonne = new Float32Array(hauteur);
  for (let y = 0; y < hauteur; y += 1) colonne[y] = valeurs[y * largeur + x];
  return colonne;
}

/** Une ligne traversée d'écriture : de l'encre en traits courts, pas en longues plages (fond, coin sombre). */
function porteDeLEncre(ligne: Float32Array, papier: number): boolean {
  const seuil = papier - ECART_D_ENCRE;
  const traitMax = Math.max(3, Math.round(ligne.length * 0.02));
  let encre = 0;
  let traits = 0;
  let plage = 0;
  for (let i = 0; i <= ligne.length; i += 1) {
    if (i < ligne.length && ligne[i] < seuil) {
      plage += 1;
      continue;
    }
    if (plage > 0 && plage <= traitMax) {
      encre += plage;
      traits += 1;
    }
    plage = 0;
  }
  return traits >= TRAITS_AU_BORD_MIN && encre / ligne.length >= ENCRE_AU_BORD_MIN;
}

/** Les bords de l'image au-delà desquels le papier continue, son écriture comprise. */
export function bordsCoupes(gris: Gris): Cote[] {
  const papier = centile(gris.valeurs, 0.9);
  const lignes = Math.min(LIGNES_DE_BORD, Math.floor(Math.min(gris.largeur, gris.hauteur) / 2));
  if (lignes < 1) return [];
  const cotes: Cote[] = ["haut", "bas", "gauche", "droite"];
  return cotes.filter((cote) => {
    // La ligne la plus extérieure dit si le papier va jusqu'au bord ; la bande, pixel le plus sombre
    // de ses lignes à chaque position, dit si de l'écriture la traverse.
    const exterieure = ligneDeBord(gris, cote, 0);
    if (centile(exterieure, 0.5) < papier - ECART_DE_PAPIER) return false;
    const bande = exterieure.slice();
    for (let rang = 1; rang < lignes; rang += 1) {
      const ligne = ligneDeBord(gris, cote, rang);
      for (let i = 0; i < bande.length; i += 1) bande[i] = Math.min(bande[i], ligne[i]);
    }
    return porteDeLEncre(bande, papier);
  });
}

/** Toutes les mesures d'une image en gris, déjà réduite pour l'analyse. */
export function mesurer(gris: Gris): Mesures {
  const [luminosite, contraste] = moyenneEtEcartType(gris.valeurs);
  let satures = 0;
  for (let i = 0; i < gris.valeurs.length; i += 1) if (gris.valeurs[i] >= SATURE) satures += 1;
  const papierSature = centile(gris.valeurs, 0.75) >= PAPIER_SATURE;
  return {
    luminosite,
    contraste,
    nettete: varianceDuLaplacien(gris),
    reflet: papierSature ? 0 : satures / Math.max(1, gris.valeurs.length),
    bordsCoupes: bordsCoupes(gris),
  };
}

/** Le verdict sur une page : ses mesures, et le grand côté de l'image d'origine, avant toute réduction. */
export function juger(mesures: Mesures, coteOriginal: number): Verdict {
  const problemes: Probleme[] = [];
  if (coteOriginal < COTE_MIN) problemes.push(probleme("resolution"));
  if (mesures.bordsCoupes.length) problemes.push(probleme("coupee"));
  if (mesures.luminosite < LUMINOSITE_MIN) problemes.push(probleme("sombre"));
  else if (mesures.contraste < CONTRASTE_MIN) problemes.push(probleme("contraste"));
  if (mesures.nettete < NETTETE_MIN) problemes.push(probleme("flou"));
  if (mesures.reflet > REFLET_MAX) problemes.push(probleme("reflet"));
  return { ok: problemes.length === 0, problemes, mesures };
}

/** Le verdict sur une image en gris, déjà réduite, dont l'originale mesurait `largeur` × `hauteur`. */
export function verifierGris(gris: Gris, largeur: number, hauteur: number): Verdict {
  return juger(mesurer(gris), Math.max(largeur, hauteur));
}

// Navigateur seulement : ce qui suit dessine sur un canvas.

function grisDe(source: CanvasImageSource, largeur: number, hauteur: number, coteMax: number): Gris | null {
  const echelle = Math.min(1, coteMax / Math.max(largeur, hauteur));
  const toile = document.createElement("canvas");
  toile.width = Math.max(1, Math.round(largeur * echelle));
  toile.height = Math.max(1, Math.round(hauteur * echelle));
  const contexte = toile.getContext("2d", { willReadFrequently: true });
  if (!contexte) return null;
  contexte.fillStyle = "#FFFFFF";
  contexte.fillRect(0, 0, toile.width, toile.height);
  contexte.drawImage(source, 0, 0, toile.width, toile.height);
  const { data } = contexte.getImageData(0, 0, toile.width, toile.height);
  return enGris(data, toile.width, toile.height);
}

/** Le verdict sur une image (une photo de la caméra, une image décodée) de `largeur` × `hauteur` px. */
export function verifierImage(source: CanvasImageSource, largeur: number, hauteur: number): Verdict {
  const gris = grisDe(source, largeur, hauteur, COTE_D_ANALYSE);
  // Sans canvas, rien ne se mesure : la page n'est pas bloquée pour une raison que l'agent ne peut corriger.
  return gris ? verifierGris(gris, largeur, hauteur) : { ok: true, problemes: [] };
}

/** Le verdict sur un fichier choisi, avant sa compression. Un PDF ne se juge qu'à son poids, ailleurs. */
export async function verifierFichier(fichier: Blob): Promise<Verdict> {
  if (fichier.type === "application/pdf") return { ok: true, problemes: [] };
  const image = await createImageBitmap(fichier, { imageOrientation: "from-image" }).catch(() => null);
  if (!image) return { ok: true, problemes: [] };
  try {
    return verifierImage(image, image.width, image.height);
  } finally {
    image.close();
  }
}

/** Pendant la visée : trop sombre ou pas, sur une vignette de la vidéo. Assez léger pour chaque demi-seconde. */
export function luminositeDuFlux(video: HTMLVideoElement): Probleme | null {
  if (!video.videoWidth) return null;
  const gris = grisDe(video, video.videoWidth, video.videoHeight, 64);
  if (!gris) return null;
  const [luminosite] = moyenneEtEcartType(gris.valeurs);
  return luminosite < LUMINOSITE_MIN ? probleme("sombre") : null;
}
