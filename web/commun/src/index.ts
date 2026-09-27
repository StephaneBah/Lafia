// Code partagé par les applications, comme commun/ l'est par les services.
// Chaque application l'importe depuis "@lafia/commun" ; Next.js le compile dans son paquet
// (transpilePackages) : rien de ce paquet n'est chargé à l'exécution. Le renouvellement du jeton,
// qui tourne avant les pages, s'importe à part : "@lafia/commun/renouvellement".
export { PageDeConnexion, type ParametresDePage } from "./connexion";
export { EtatDeLActeur } from "./etat";
// Ce qu'une application lit elle-même de sa session, pour ses propres pages.
export { COOKIE_DE_SESSION, identiteParLaPasserelle, type Session, type SessionAgent } from "./service";
export { adresseDuSite } from "./site";
// Les pages d'un Document (ADR 0008) : les préparer dans le navigateur avant l'envoi (numerisation,
// soin), et les relayer depuis le serveur (soin, citoyen). Un composant du navigateur importe la
// préparation par "@lafia/commun/televersement", pour ne rien tirer du serveur dans son paquet.
export { compresser, enKo, enMo, PageRefusee, PAGES_MAX, POIDS_MAX, preparerFichier, TYPES_ACCEPTES } from "./televersement";
export { servirUnePage } from "./pages";
