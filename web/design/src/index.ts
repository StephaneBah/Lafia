// Le système de design Lafia : jetons (styles.css), composants et formats. Chaque application et le
// site les importent depuis "@lafia/design" ; Next.js les compile dans son paquet (transpilePackages) :
// rien de ce paquet n'est chargé à l'exécution. Les illustrations ont leur propre point d'entrée,
// "@lafia/design/illustration", réservé aux composants serveur.

export { ACTEURS, ORDRE_DES_ACTEURS, adresse, hoteDApplication, type Acteur } from "./acteurs";
export { Button } from "./Button";
export { CodeField, NpiField, TextInput } from "./champs";
export { DemoAccount, type CompteAffiche } from "./DemoAccount";
export { LONGUEUR_NPI, formatDate, formatFcfa, formatNpi } from "./formats";
export type { NomIcone } from "./generes/icones";
export type { NomPictogramme } from "./generes/pictogrammes";
export { Icon } from "./Icon";
export { Logo } from "./Logo";
export { OrdonnanceLine } from "./OrdonnanceLine";
export { Picto } from "./Picto";
export { AppHeader, ServiceCard, SiteFooter, SoonCard } from "./portes";
export { SiteHeader } from "./SiteHeader";
export { Posology, StatusBadge, type Moment, type Posologie, type Status } from "./statuts";
export { Alert, Card, Table, TimelineItem, type Colonne, type Rangee } from "./structure";
