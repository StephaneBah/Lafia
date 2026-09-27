import { EtatDeLActeur } from "@lafia/commun";

/** L'accueil de la relecture : l'état du service et qui est connecté (le triage et la validation viennent avec F6.4). */
export default function Accueil() {
  return <EtatDeLActeur titre="Relecture" service="relecture" avecConnexion />;
}
