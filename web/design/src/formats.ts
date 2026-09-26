// Formats d'affichage de la charte : montants, NPI, dates. Rien ici ne change une donnée envoyée à un
// service : un NPI part toujours en treize chiffres, jamais groupé.

/** Espace fine insécable entre les milliers, espace insécable avant l'unité : `12 500 FCFA`. */
export function formatFcfa(montant: number): string {
  return `${String(Math.round(montant)).replace(/\B(?=(\d{3})+(?!\d))/g, " ")} FCFA`;
}

/** Longueur d'un NPI, et ses groupes pour la lecture à voix haute : `0000 001 204 815`. */
export const LONGUEUR_NPI = 13;
const GROUPES_NPI = [4, 3, 3, 3];

/** Les chiffres d'un NPI, en groupes 4-3-3-3 ; accepte un NPI incomplet, pendant la frappe. */
export function formatNpi(saisie: string): string {
  const chiffres = saisie.replace(/\D/g, "").slice(0, LONGUEUR_NPI);
  const groupes: string[] = [];
  let debut = 0;
  for (const taille of GROUPES_NPI) {
    if (debut < chiffres.length) groupes.push(chiffres.slice(debut, debut + taille));
    debut += taille;
  }
  return groupes.join(" ");
}

/** Une date ISO (`2026-09-25` ou `2026-09-25T10:00:00Z`) en `25/09/2026`, sans décalage de fuseau. */
export function formatDate(iso: string): string {
  const [annee, mois, jour] = iso.slice(0, 10).split("-");
  return `${jour}/${mois}/${annee}`;
}
