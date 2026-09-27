import { EtatDeLActeur } from "@lafia/commun";

/** L'accueil du guichet de numérisation : l'état du service et qui est connecté (le parcours du guichet vient avec F5.3). */
export default function Accueil() {
  return <EtatDeLActeur titre="Numérisation" service="numerisation" avecConnexion />;
}
