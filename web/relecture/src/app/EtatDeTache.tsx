// L'état d'une tâche : icône, mot et couleur, toujours ensemble ; la couleur ne porte jamais le sens seule.
import { Icon } from "@lafia/design";

import { etatDeLaTache } from "../libelles";
import type { Tache } from "../types";

const TONS = { "a-faire": "lf-tone-apayer", renvoyee: "lf-tone-danger", faite: "lf-tone-paye" } as const;

export function EtatDeTache({ tache }: { tache: Pick<Tache, "etape" | "statut" | "renvoyee"> }) {
  const etat = etatDeLaTache(tache);
  return (
    <span className={`lf-badge lf-badge--pro ${TONS[etat.ton]}`}>
      <Icon name={etat.icone} size={16} />
      <span>{etat.libelle}</span>
    </span>
  );
}
