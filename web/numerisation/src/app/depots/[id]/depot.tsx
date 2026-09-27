// Ce que chaque écran d'un dépôt lit d'abord : le dépôt lui-même, ou pourquoi il ne se lit pas.
import { Alert, Button } from "@lafia/design";
import { redirect } from "next/navigation";
import type { ReactNode } from "react";

import { lireDepot, type Depot } from "../../../numerisation";

export type ParametresDuDepot = {
  params: Promise<{ id: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

/** Le dépôt, ou l'écran qui dit pourquoi il ne s'ouvre pas et par où continuer. */
export async function depotOuRefus(depot: string, ici: string): Promise<{ depot: Depot } | { refus: ReactNode }> {
  const reponse = await lireDepot(depot);
  if (reponse.ok) return { depot: reponse.corps };
  if (reponse.statut === 401) redirect("/connexion");
  if (reponse.statut === 0 || reponse.statut >= 500) {
    return {
      refus: (
        <Alert
          tone="danger"
          title="Le service numérisation ne répond pas."
          actions={
            <Button href={ici} size="pro" variant="secondary" icon="arrow-left">
              Réessayer
            </Button>
          }
        >
          Les Documents déjà enregistrés sont gardés. Réessayez dans un instant.
        </Alert>
      ),
    };
  }
  return { refus: <DepotClos /> };
}

/** Un dépôt clos, ou ouvert par un autre agent : il ne se lit plus et ne se complète plus. */
export function DepotClos() {
  return (
    <Alert
      tone="attention"
      title="Ce dépôt est clos : il ne se complète plus."
      actions={
        <Button href="/" size="pro" icon="plus">
          Accueillir une personne
        </Button>
      }
    >
      Un dépôt se complète seulement par l'agent qui l'a ouvert, jusqu'à sa clôture. Pour d'autres papiers, ouvrez un
      nouveau dépôt.
    </Alert>
  );
}
