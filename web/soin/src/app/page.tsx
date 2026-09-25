import { connection } from "next/server";

import { lireSante, type Sante } from "../service";

function etatNoyau(sante: Sante | null): string {
  if (!sante) return "inconnu";
  if (sante.noyau.statut === "disponible") return `disponible, FHIR ${sante.noyau.version_fhir}`;
  return sante.noyau.statut;
}

export default async function Accueil() {
  // Rendue à chaque requête : la page montre l'état du moment, jamais celui de la construction.
  await connection();
  const sante = await lireSante();

  return (
    <main>
      <p>Lafia</p>
      <h1>Soin</h1>
      <dl>
        <dt>Service soin</dt>
        <dd>{sante?.statut ?? "injoignable"}</dd>
        <dt>Noyau</dt>
        <dd>{etatNoyau(sante)}</dd>
      </dl>
    </main>
  );
}
