// Un QR code minimal, sans dépendance : version 1 (21 × 21), correction M, mode octet, masque 0.
// Assez pour un numéro d'ordonnance (`ORD-7K4-M2P`, 11 caractères ; 14 au plus). Algorithme de la
// norme ISO/IEC 18004, dans l'ordre de l'implémentation de référence de Nayuki.

const TAILLE = 21;
const OCTETS_DE_DONNEES = 16;
const OCTETS_DE_CORRECTION = 10;
const MAX = 14;
/** Bits de format, correction M et masque 0, déjà masqués (0x5412). */
const FORMAT = 0x5412;

function multiplier(x: number, y: number): number {
  let z = 0;
  for (let i = 7; i >= 0; i--) {
    z = (z << 1) ^ ((z >>> 7) * 0x11d);
    z ^= ((y >>> i) & 1) * x;
  }
  return z & 0xff;
}

function diviseur(degre: number): number[] {
  const resultat = new Array<number>(degre).fill(0);
  resultat[degre - 1] = 1;
  let racine = 1;
  for (let i = 0; i < degre; i++) {
    for (let j = 0; j < degre; j++) {
      resultat[j] = multiplier(resultat[j], racine);
      if (j + 1 < degre) resultat[j] ^= resultat[j + 1];
    }
    racine = multiplier(racine, 0x02);
  }
  return resultat;
}

function reste(donnees: number[], div: number[]): number[] {
  const resultat = div.map(() => 0);
  for (const octet of donnees) {
    const facteur = octet ^ (resultat.shift() as number);
    resultat.push(0);
    div.forEach((coef, i) => (resultat[i] ^= multiplier(coef, facteur)));
  }
  return resultat;
}

function motsDeCode(texte: string): number[] {
  const octets = Array.from(new TextEncoder().encode(texte));
  if (octets.length > MAX) throw new Error("texte trop long pour un QR de version 1");
  const bits: number[] = [];
  const ajouter = (valeur: number, longueur: number) => {
    for (let i = longueur - 1; i >= 0; i--) bits.push((valeur >>> i) & 1);
  };
  ajouter(0b0100, 4);
  ajouter(octets.length, 8);
  octets.forEach((o) => ajouter(o, 8));
  ajouter(0, Math.min(4, OCTETS_DE_DONNEES * 8 - bits.length));
  while (bits.length % 8) bits.push(0);
  const donnees: number[] = [];
  for (let i = 0; i < bits.length; i += 8) donnees.push(bits.slice(i, i + 8).reduce((a, b) => (a << 1) | b, 0));
  for (let bourrage = 0xec; donnees.length < OCTETS_DE_DONNEES; bourrage ^= 0xec ^ 0x11) donnees.push(bourrage);
  return [...donnees, ...reste(donnees, diviseur(OCTETS_DE_CORRECTION))];
}

/** Les modules du QR de `texte`, ligne par ligne : `true` pour un module noir. */
export function matriceQr(texte: string): boolean[][] {
  const modules = Array.from({ length: TAILLE }, () => new Array<boolean>(TAILLE).fill(false));
  const fonction = Array.from({ length: TAILLE }, () => new Array<boolean>(TAILLE).fill(false));
  const poser = (x: number, y: number, noir: boolean) => {
    modules[y][x] = noir;
    fonction[y][x] = true;
  };
  for (let i = 0; i < TAILLE; i++) {
    poser(6, i, i % 2 === 0);
    poser(i, 6, i % 2 === 0);
  }
  for (const [cx, cy] of [
    [3, 3],
    [TAILLE - 4, 3],
    [3, TAILLE - 4],
  ]) {
    for (let dy = -4; dy <= 4; dy++) {
      for (let dx = -4; dx <= 4; dx++) {
        const x = cx + dx;
        const y = cy + dy;
        const distance = Math.max(Math.abs(dx), Math.abs(dy));
        if (x >= 0 && x < TAILLE && y >= 0 && y < TAILLE) poser(x, y, distance !== 2 && distance !== 4);
      }
    }
  }
  const bit = (i: number) => ((FORMAT >>> i) & 1) === 1;
  for (let i = 0; i <= 5; i++) poser(8, i, bit(i));
  poser(8, 7, bit(6));
  poser(8, 8, bit(7));
  poser(7, 8, bit(8));
  for (let i = 9; i < 15; i++) poser(14 - i, 8, bit(i));
  for (let i = 0; i < 8; i++) poser(TAILLE - 1 - i, 8, bit(i));
  for (let i = 8; i < 15; i++) poser(8, TAILLE - 15 + i, bit(i));
  poser(8, TAILLE - 8, true);

  const donnees = motsDeCode(texte);
  let i = 0;
  for (let droite = TAILLE - 1; droite >= 1; droite -= 2) {
    if (droite === 6) droite = 5;
    for (let vertical = 0; vertical < TAILLE; vertical++) {
      for (let j = 0; j < 2; j++) {
        const x = droite - j;
        const montant = ((droite + 1) & 2) === 0;
        const y = montant ? TAILLE - 1 - vertical : vertical;
        if (!fonction[y][x] && i < donnees.length * 8) {
          modules[y][x] = ((donnees[i >>> 3] >>> (7 - (i & 7))) & 1) === 1;
          i++;
        }
      }
    }
  }
  for (let y = 0; y < TAILLE; y++) {
    for (let x = 0; x < TAILLE; x++) {
      if (!fonction[y][x] && (x + y) % 2 === 0) modules[y][x] = !modules[y][x];
    }
  }
  return modules;
}

/** Le tracé SVG des modules noirs, marge de 4 modules comprise : un seul `path`, dans un carré de 29. */
export function traceQr(texte: string): { chemin: string; cote: number } {
  const marge = 4;
  const modules = matriceQr(texte);
  let chemin = "";
  modules.forEach((ligne, y) =>
    ligne.forEach((noir, x) => {
      if (noir) chemin += `M${x + marge} ${y + marge}h1v1h-1z`;
    }),
  );
  return { chemin, cote: TAILLE + 2 * marge };
}
