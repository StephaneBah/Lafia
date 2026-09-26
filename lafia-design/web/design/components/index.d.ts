/** Lafia — composants partagés (web/design). window.Lafia. React 18. */
import type { ReactNode } from 'react';
type Size = 'citizen' | 'pro';
type Actor = 'citoyen' | 'soin' | 'caisse' | 'pharmacie';
type PictoName = 'matin' | 'midi' | 'soir' | 'nuit' | 'avant-repas' | 'apres-repas' | 'comprime' | 'comprime-demi' | 'jours' | 'a-payer' | 'paye' | 'a-retirer' | 'retire-partie' | 'retire' | 'allergie' | 'urgence' | 'consultation';
type Status = 'apayer' | 'paye' | 'aretirer' | 'partiel' | 'retire' | 'allergie' | 'urgence' | 'encours' | 'termine' | 'attente' | 'resultat';
/** Logotype Lafia. */
export function Logo(p: { tone?: 'royal' | 'blanc' | 'noir'; height?: number; href?: string; linkLabel?: string; animate?: boolean }): JSX.Element;
/** Icône Phosphor (bold ; duotone près des illustrations). */
export function Icon(p: { name: string; size?: number; duotone?: boolean; label?: string; className?: string }): JSX.Element;
/** Pictogramme Lafia (grille 48). */
export function Picto(p: { name: PictoName; size?: number; label?: string; decorative?: boolean }): JSX.Element;
/** Posologie en pictogrammes. */
export function Posology(p: { count?: number; moments?: Array<'matin' | 'midi' | 'soir' | 'nuit'>; meal?: 'avant' | 'apres'; days?: number; size?: number }): JSX.Element;
/** Bouton. */
export function Button(p: { variant?: 'primary' | 'secondary' | 'ghost' | 'danger'; size?: Size; icon?: string; iconRight?: string; loading?: boolean; disabled?: boolean; block?: boolean; href?: string; onClick?: () => void; children: ReactNode }): JSX.Element;
/** Champ texte. */
export function TextInput(p: { label: string; hint?: string; error?: string; size?: Size; icon?: string; [attr: string]: unknown }): JSX.Element;
/** Champ NPI : 13 chiffres groupés 4-3-3-3. onChange reçoit les chiffres seuls. */
export function NpiField(p: { value?: string; defaultValue?: string; onChange?: (digits: string) => void; onComplete?: (npi: string) => void; label?: string; hint?: string; error?: string; size?: Size; autoFocus?: boolean }): JSX.Element;
/** Code carnet case par case. */
export function CodeField(p: { length?: number; value?: string; defaultValue?: string; onChange?: (code: string) => void; numeric?: boolean; label?: string; hint?: string; error?: string; size?: Size }): JSX.Element;
/** Statut : pictogramme + mot + couleur. */
export function StatusBadge(p: { status: Status; size?: 'citizen' | 'large' | 'pro'; label?: string }): JSX.Element;
/** Ligne d'ordonnance. */
export function OrdonnanceLine(p: { name: string; detail?: string; mode?: 'citoyen' | 'caisse' | 'pharmacie'; price?: number; status?: Status; posology?: Parameters<typeof Posology>[0]; allergy?: string; checked?: boolean; onToggle?: (next: boolean) => void; disabled?: boolean }): JSX.Element;
/** Étape de cas de visite sur le fil. À placer dans <ol class="lf-timeline">. */
export function TimelineItem(p: { title: ReactNode; date?: string; place?: string; icon?: string; state?: 'done' | 'current' | 'upcoming'; first?: boolean; last?: boolean; animate?: boolean; index?: number; children?: ReactNode }): JSX.Element;
/** Alerte persistante. */
export function Alert(p: { tone?: 'info' | 'succes' | 'attention' | 'danger' | 'allergie' | 'urgence'; title?: ReactNode; children?: ReactNode; actions?: ReactNode; onClose?: () => void }): JSX.Element;
/** Carte. */
export function Card(p: { tone?: 'soft' | 'ardoise'; interactive?: boolean; href?: string; dense?: boolean; loading?: boolean; as?: string; children?: ReactNode }): JSX.Element;
/** Tableau pro. */
export function Table(p: { columns: Array<{ key: string; label: string; align?: 'end'; mono?: boolean }>; rows?: Array<Record<string, ReactNode> & { id?: string; selected?: boolean }>; caption?: string; dense?: boolean; loading?: boolean; empty?: string }): JSX.Element;
/** En-tête du site produit. */
export function SiteHeader(p: { links?: Array<{ label: string; href: string }>; ctaHref?: string; ctaLabel?: string; homeHref?: string; sticky?: boolean }): JSX.Element;
/** Pied de page du site produit. */
export function SiteFooter(p: { note?: string }): JSX.Element;
/** En-tête d'application. */
export function AppHeader(p: { actor: Actor; actorLabel?: string; place?: string; user?: string; onSignOut?: () => void; siteHref?: string }): JSX.Element;
/** Carte de service (porte vers une application). */
export function ServiceCard(p: { actor: Actor; title?: string; forWhom: string; description: string; address?: string; href?: string; illustration?: ReactNode; demo?: false | { identifier?: string; password?: string; open?: boolean } }): JSX.Element;
/** Compte de démonstration repliable. */
export function DemoAccount(p: { identifier?: string; password?: string | false; identifierLabel?: string; passwordLabel?: string; note?: string; open?: boolean; summary?: string }): JSX.Element;
/** Service à venir (« Bientôt »). */
export function SoonCard(p: { title: string; tagline?: string; icon?: string; children?: ReactNode }): JSX.Element;
export function formatFcfa(n: number): string;
export function formatNpi(digits: string): string;
