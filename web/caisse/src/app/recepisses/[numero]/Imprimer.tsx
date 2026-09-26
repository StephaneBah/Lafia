"use client";

import { Button } from "@lafia/design";

/** Imprime le récépissé : la feuille d'impression ne garde que lui. */
export function Imprimer() {
  return (
    <Button size="pro" icon="printer" onClick={() => window.print()}>
      Imprimer le récépissé
    </Button>
  );
}
