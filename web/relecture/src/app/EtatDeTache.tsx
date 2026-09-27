// L'état d'une tâche : icône, mot et couleur, toujours ensemble ; la couleur ne porte jamais le sens seule.
import { Icon } from "@lafia/design";

import type { Tache } from "../relecture";

export function libelleDeLEtat(tache: Pick<Tache, "etape" | "verdict">): string {
  const faite = Boolean(tache.verdict);
  if (tache.etape === "triage") return faite ? "Trié" : "À trier";
  return faite ? "Validé" : "À valider";
}

export function EtatDeTache({ tache }: { tache: Pick<Tache, "etape" | "verdict"> }) {
  const faite = Boolean(tache.verdict);
  return (
    <span className={`lf-badge lf-badge--pro ${faite ? "lf-tone-paye" : "lf-tone-apayer"}`}>
      <Icon name={faite ? "check" : "clock"} size={16} />
      <span>{libelleDeLEtat(tache)}</span>
    </span>
  );
}
