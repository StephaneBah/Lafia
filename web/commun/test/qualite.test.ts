// Les contrôles de la capture (src/qualite.ts), sur des pages de synthèse : aucun papier réel n'entre
// ici. `npm test -w @lafia/commun` (node --test, types retirés à la volée).
import assert from "node:assert/strict";
import { test } from "node:test";

import { COTE_MIN, verifierGris, type CodeDeProbleme, type Gris } from "../src/qualite.ts";

const LARGEUR = 600;
const HAUTEUR = 800;
const FOND = 60;
const PAPIER = 215;
const ENCRE = 40;

type Page = { gauche: number; haut: number; droite: number; bas: number };
const BIEN_CADREE: Page = { gauche: 60, haut: 60, droite: 540, bas: 740 };

/** Une page de papier sur un fond sombre, écrite de lignes de traits courts jusqu'à ses marges. */
function page(cadre: Page = BIEN_CADREE, { fond = FOND, papier = PAPIER, marge = 30 } = {}): Gris {
  const valeurs = new Float32Array(LARGEUR * HAUTEUR).fill(fond);
  for (let y = Math.max(0, cadre.haut); y < Math.min(HAUTEUR, cadre.bas); y += 1) {
    for (let x = Math.max(0, cadre.gauche); x < Math.min(LARGEUR, cadre.droite); x += 1) valeurs[y * LARGEUR + x] = papier;
  }
  for (let ligne = cadre.haut + marge; ligne + 14 < cadre.bas - marge; ligne += 28) {
    for (let x = cadre.gauche + marge; x + 3 < cadre.droite - marge; x += 9) {
      if ((x * 7 + ligne) % 5 === 0) continue; // des espaces entre les mots
      for (let y = ligne; y < ligne + 14; y += 1) {
        for (let dx = 0; dx < 3; dx += 1) {
          const xx = x + dx;
          if (y >= 0 && y < HAUTEUR && xx >= 0 && xx < LARGEUR) valeurs[y * LARGEUR + xx] = ENCRE;
        }
      }
    }
  }
  return { largeur: LARGEUR, hauteur: HAUTEUR, valeurs };
}

function flouter(gris: Gris, rayon: number): Gris {
  const { largeur, hauteur } = gris;
  let courant = gris.valeurs;
  for (const [dx, dy] of [[1, 0], [0, 1]]) {
    const suivant = new Float32Array(courant.length);
    for (let y = 0; y < hauteur; y += 1) {
      for (let x = 0; x < largeur; x += 1) {
        let somme = 0;
        let n = 0;
        for (let k = -rayon; k <= rayon; k += 1) {
          const xx = x + k * dx;
          const yy = y + k * dy;
          if (xx < 0 || yy < 0 || xx >= largeur || yy >= hauteur) continue;
          somme += courant[yy * largeur + xx];
          n += 1;
        }
        suivant[y * largeur + x] = somme / n;
      }
    }
    courant = suivant;
  }
  return { largeur, hauteur, valeurs: courant };
}

function transformer(gris: Gris, f: (v: number, x: number, y: number) => number): Gris {
  const valeurs = gris.valeurs.map((v, i) => f(v, i % gris.largeur, Math.floor(i / gris.largeur)));
  return { ...gris, valeurs };
}

function codes(gris: Gris, cote = 1600): CodeDeProbleme[] {
  return verifierGris(gris, cote, cote).problemes.map((p) => p.code);
}

test("une page nette, claire, entière, sans reflet, est gardée", () => {
  const verdict = verifierGris(page(), 1200, 1600);
  assert.deepEqual(verdict.problemes, [], JSON.stringify(verdict.mesures));
  assert.equal(verdict.ok, true);
});

test("une image de moins de 1200 px de grand côté est refusée", () => {
  assert.deepEqual(codes(page(), COTE_MIN - 1), ["resolution"]);
});

test("une page floue est refusée", () => {
  assert.deepEqual(codes(flouter(page(), 3)), ["flou"]);
});

test("une page trop sombre est refusée, avec son conseil", () => {
  const verdict = verifierGris(transformer(page(), (v) => v * 0.25), 1600, 1600);
  assert.ok(verdict.problemes.some((p) => p.code === "sombre" && p.message.startsWith("Trop sombre")));
});

test("une page voilée, sans contraste, est refusée", () => {
  assert.ok(codes(transformer(page(), (v) => 150 + (v - 150) * 0.1)).includes("contraste"));
});

test("un reflet sur la page est refusé", () => {
  const reflet = transformer(page(), (v, x, y) => ((x - 300) ** 2 + (y - 400) ** 2 < 70 ** 2 ? 255 : v));
  assert.deepEqual(codes(reflet), ["reflet"]);
});

test("une page dont l'écriture sort du cadre est coupée", () => {
  const coupee = page({ ...BIEN_CADREE, droite: 700 }, { marge: 30 });
  const verdict = verifierGris(coupee, 1600, 1600);
  assert.deepEqual(verdict.mesures?.bordsCoupes, ["droite"]);
  assert.equal(verdict.problemes[0].message, "Page coupée : reculez pour voir les quatre bords");
});

test("un scan blanc jusqu'au bord, aux marges vides, n'est ni coupé ni ébloui", () => {
  const scan = page({ gauche: 0, haut: 0, droite: LARGEUR, bas: HAUTEUR }, { papier: 255, marge: 40 });
  assert.deepEqual(codes(scan), []);
});

test("le coin sombre d'une page penchée n'est pas une page coupée", () => {
  const penchee = transformer(page({ gauche: 0, haut: 0, droite: LARGEUR, bas: HAUTEUR }, { marge: 40 }), (v, x, y) =>
    x + y < 120 || LARGEUR - x + y < 90 ? FOND : v,
  );
  assert.deepEqual(codes(penchee), []);
});
