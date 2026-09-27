// Les pages d'un Document, préparées dans le navigateur avant l'envoi (ADR 0008), au guichet de
// numérisation comme au service soin : une image devient un JPEG d'au plus 1600 px sur son grand côté,
// sur fond blanc, dont la qualité descend jusqu'à peser 1 Mo ; un PDF part tel quel, s'il pèse au plus
// 3 Mo. Le service refuse ce qui dépasse ; ici, l'utilisateur l'apprend avant d'envoyer.
// Navigateur seulement : ce module dessine sur un canvas et n'importe rien du serveur.

export const COTE_MAX = 1600;
export const POIDS_VISE = 1_000_000;
export const POIDS_MAX = 3_000_000;
export const PAGES_MAX = 20;
export const TYPES_ACCEPTES = ["image/jpeg", "image/png", "application/pdf"];

const QUALITES = [0.85, 0.75, 0.65, 0.55, 0.45, 0.35];

/** Une page trop lourde, même compressée, ou un fichier d'un autre format. */
export class PageRefusee extends Error {}

function versBlob(toile: HTMLCanvasElement, qualite: number): Promise<Blob> {
  return new Promise((resoudre, rejeter) =>
    toile.toBlob((blob) => (blob ? resoudre(blob) : rejeter(new PageRefusee("Image illisible."))), "image/jpeg", qualite),
  );
}

/** Dessine `source` réduite à 1600 px sur son grand côté, puis la compresse en JPEG jusqu'à 1 Mo. */
export async function compresser(source: CanvasImageSource, largeur: number, hauteur: number): Promise<Blob> {
  const echelle = Math.min(1, COTE_MAX / Math.max(largeur, hauteur));
  const toile = document.createElement("canvas");
  toile.width = Math.max(1, Math.round(largeur * echelle));
  toile.height = Math.max(1, Math.round(hauteur * echelle));
  const contexte = toile.getContext("2d");
  if (!contexte) throw new PageRefusee("Image illisible.");
  // Un PNG transparent sur fond blanc, comme le papier.
  contexte.fillStyle = "#FFFFFF";
  contexte.fillRect(0, 0, toile.width, toile.height);
  contexte.drawImage(source, 0, 0, toile.width, toile.height);

  let blob: Blob | null = null;
  for (const qualite of QUALITES) {
    blob = await versBlob(toile, qualite);
    if (blob.size <= POIDS_VISE) return blob;
  }
  if (blob && blob.size <= POIDS_MAX) return blob;
  throw new PageRefusee("Cette page reste trop lourde, même compressée.");
}

/** Un fichier choisi : une image compressée, ou un PDF d'au plus 3 Mo. */
export async function preparerFichier(fichier: File): Promise<Blob> {
  if (!TYPES_ACCEPTES.includes(fichier.type)) {
    throw new PageRefusee(`« ${fichier.name} » n'est ni une photo JPEG ou PNG, ni un PDF.`);
  }
  if (fichier.type === "application/pdf") {
    if (fichier.size > POIDS_MAX) {
      throw new PageRefusee(`« ${fichier.name} » pèse ${enMo(fichier.size)} : un PDF peut peser 3 Mo au plus. Photographiez plutôt ses pages.`);
    }
    return fichier;
  }
  // Tournée selon ses métadonnées : une photo prise en portrait reste en portrait.
  const image = await createImageBitmap(fichier, { imageOrientation: "from-image" }).catch(() => {
    throw new PageRefusee(`« ${fichier.name} » ne s'ouvre pas comme une image.`);
  });
  try {
    return await compresser(image, image.width, image.height);
  } finally {
    image.close();
  }
}

export function enMo(octets: number): string {
  const mo = octets / 1_000_000;
  return `${mo.toLocaleString("fr-FR", { maximumFractionDigits: 1, minimumFractionDigits: mo < 10 ? 1 : 0 })} Mo`;
}

export function enKo(octets: number): string {
  return octets < 1_000_000 ? `${Math.max(1, Math.round(octets / 1000))} ko` : enMo(octets);
}
