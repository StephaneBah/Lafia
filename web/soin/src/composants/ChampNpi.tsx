"use client";

import { NpiField } from "@lafia/design";

/** Le NPI de la recherche : le formulaire part dès le treizième chiffre. */
export function ChampNpi() {
  return (
    <NpiField
      name="npi"
      size="pro"
      label="NPI du patient"
      hint="Treize chiffres : le patient s’ouvre dès le dernier."
      autoFocus
      required
      onComplete={() => {
        const champ = document.activeElement as HTMLInputElement | null;
        // Laisse le champ caché prendre la valeur complète avant l'envoi.
        setTimeout(() => champ?.form?.requestSubmit(), 0);
      }}
    />
  );
}
