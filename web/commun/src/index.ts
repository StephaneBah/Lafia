// Code partagé par les applications, comme commun/ l'est par les services.
// Chaque application l'importe depuis "@lafia/commun" ; Next.js le compile dans son paquet
// (transpilePackages) : rien de ce paquet n'est chargé à l'exécution. Le renouvellement du jeton,
// qui tourne avant les pages, s'importe à part : "@lafia/commun/renouvellement".
export { PageDeConnexion, type ParametresDePage } from "./connexion";
export { EtatDeLActeur } from "./etat";
