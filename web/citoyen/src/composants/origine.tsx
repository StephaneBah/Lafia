import { Icon, type NomIcone } from "@lafia/design";

import type { Origine } from "../lib/carnet";

// D'où vient une information du carnet (ADR 0007), dite en mots simples, avec une icône : le citoyen
// sait ce qu'un soignant a relevé, ce qu'il a dit lui-même, et ce qui vient d'un ancien papier.
const ORIGINES: Record<string, { mots: string; icone: NomIcone }> = {
  visite: { mots: "Relevé en visite", icone: "stethoscope" },
  declaration: { mots: "Déclaré par vous", icone: "user" },
  report: { mots: "Reporté depuis un document", icone: "arrow-square-out" },
  numerisation: { mots: "Numérisé", icone: "copy" },
};

/** L'origine d'une entrée ; rien pour une entrée d'avant, qui n'en porte pas. */
export function OrigineEnMots({ origine }: { origine: Origine }) {
  const connue = origine ? ORIGINES[origine] : undefined;
  if (!connue) return null;
  return (
    <span className="carnet-origine">
      <Icon name={connue.icone} size={18} />
      {connue.mots}
    </span>
  );
}
