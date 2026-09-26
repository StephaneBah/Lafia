"use client";

import { Button } from "@lafia/design";

/** Remplit le formulaire de connexion avec un compte de démonstration ; il ne reste qu'à valider. */
export function UtiliserCeCompte({ formulaire, identifiant, motDePasse }: { formulaire: string; identifiant: string; motDePasse: string }) {
  function remplir() {
    const cible = document.getElementById(formulaire);
    if (!(cible instanceof HTMLFormElement)) return;
    for (const [nom, valeur] of [
      ["identifiant", identifiant],
      ["mot_de_passe", motDePasse],
    ]) {
      const champ = cible.elements.namedItem(nom);
      if (champ instanceof HTMLInputElement) champ.value = valeur;
    }
    cible.querySelector<HTMLButtonElement>('button[type="submit"]')?.focus();
  }
  return (
    <Button size="pro" variant="secondary" onClick={remplir} aria-label={`Utiliser le compte ${identifiant}`}>
      Utiliser
    </Button>
  );
}
