// Code partagé par les applications, comme commun/ l'est par les services.
// Chaque application l'importe depuis "@lafia/commun" ; Next.js le compile dans son paquet
// (transpilePackages) : rien de ce paquet n'est chargé à l'exécution.
export { EtatDeLActeur } from "./etat";
