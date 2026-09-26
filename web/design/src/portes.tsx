// Les portes vers les applications : en-tête d'application, pied du site, carte de service, carte
// « Bientôt ». Les adresses se déduisent du domaine (LAFIA_DOMAINE) : localhost en local.

import type { ReactNode } from "react";

import { ACTEURS, ORDRE_DES_ACTEURS, adresse, hoteDApplication, type Acteur } from "./acteurs";
import { DemoAccount, type CompteAffiche } from "./DemoAccount";
import type { NomIcone } from "./generes/icones";
import { Icon } from "./Icon";
import { Logo } from "./Logo";

/**
 * En-tête d'application : le logo ramène au site, l'acteur est toujours nommé. `signOut` : un
 * formulaire qui ferme la session auprès d'identite, par la passerelle de l'application.
 */
export function AppHeader({
  actor,
  actorLabel,
  place,
  user,
  signOut = false,
  siteHref,
}: {
  actor: Acteur;
  actorLabel?: string;
  place?: string;
  user?: string;
  /** `true` : `POST /api/identite/deconnexion` ; une chaîne : une autre adresse d'envoi. */
  signOut?: boolean | string;
  siteHref: string;
}) {
  const acteur = ACTEURS[actor];
  return (
    <header className={actor === "citoyen" ? "lf-appheader lf-appheader--citizen" : "lf-appheader"}>
      <Logo tone="blanc" height={26} href={siteHref} />
      <span className="lf-appheader-actor">
        <Icon name={acteur.icone} size={20} />
        <span>{actorLabel ?? acteur.libelle}</span>
      </span>
      {place && <span className="lf-appheader-place">{place}</span>}
      <span className="lf-appheader-spacer" />
      {user && (
        <span className="lf-appheader-user">
          <Icon name="user" size={20} />
          <span>{user}</span>
        </span>
      )}
      {signOut && (
        <form method="post" action={typeof signOut === "string" ? signOut : "/api/identite/deconnexion"}>
          <button type="submit" className="lf-appheader-out">
            <Icon name="sign-out" size={20} />
            <span>Se déconnecter</span>
          </button>
        </form>
      )}
    </header>
  );
}

/** Pied du site produit : chaque application à son adresse, et le code source. */
export function SiteFooter({ domaine, note }: { domaine: string; note?: string }) {
  return (
    <footer className="lf-sitefooter">
      <div className="lf-sitefooter-in">
        <div className="lf-sitefooter-brand">
          <Logo tone="blanc" height={36} />
          <p>{note ?? "Prototype de démonstration : toutes les données sont fictives."}</p>
        </div>
        <nav aria-label="Applications">
          <ul>
            {ORDRE_DES_ACTEURS.map((acteur) => (
              <li key={acteur}>
                <a href={adresse(domaine, acteur)}>
                  <span>{ACTEURS[acteur].libelle}</span>
                  <span className="lf-mono">{hoteDApplication(acteur, domaine)}</span>
                </a>
              </li>
            ))}
          </ul>
        </nav>
        <a className="lf-sitefooter-gh" href="https://github.com/StephaneBah/Lafia">
          <Icon name="github-logo" size={20} />
          <span>Code source sur GitHub</span>
        </a>
      </div>
    </footer>
  );
}

/** Un nom d'hôte coupable après chaque point, pour qu'il tienne à 360px sans déborder. */
function hoteSecable(hote: string): ReactNode {
  return hote.split(".").map((partie, i, parties) => (
    <span key={i}>
      {partie}
      {i < parties.length - 1 && (
        <>
          .<wbr />
        </>
      )}
    </span>
  ));
}

/** Carte de service : la porte vers une application, avec son adresse et ses comptes de démonstration. */
export function ServiceCard({
  actor,
  domaine,
  title,
  forWhom,
  description,
  illustration,
  demo,
  demoNote,
}: {
  actor: Acteur;
  domaine: string;
  title?: string;
  forWhom: string;
  description: string;
  illustration?: ReactNode;
  demo?: CompteAffiche[];
  demoNote?: ReactNode;
}) {
  const acteur = ACTEURS[actor];
  const libelle = title ?? acteur.libelle;
  const hote = hoteDApplication(actor, domaine);
  return (
    <div className="lf-service">
      <a className="lf-service-card" href={adresse(domaine, actor)} aria-label={`${libelle}, ${forWhom.toLowerCase()} : ouvrir ${hote}`}>
        <div className="lf-service-illu" aria-hidden="true">
          {illustration ?? <Icon name={acteur.icone} duotone size={72} />}
        </div>
        <div className="lf-service-for">{forWhom}</div>
        <div className="lf-service-title">{libelle}</div>
        <p className="lf-service-desc">{description}</p>
        <div className="lf-service-foot">
          <span className="lf-mono lf-service-addr">{hoteSecable(hote)}</span>
          <span className="lf-service-open">
            <span>Ouvrir</span>
            <Icon name="arrow-square-out" size={20} />
          </span>
        </div>
      </a>
      {demo && demo.length > 0 && <DemoAccount comptes={demo} note={demoNote} />}
    </div>
  );
}

/** Service à venir : surface pervenche, badge « Bientôt », aucun bouton. */
export function SoonCard({
  title,
  tagline,
  icon = "plus",
  illustration,
  children,
}: {
  title: string;
  tagline?: string;
  icon?: NomIcone;
  illustration?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <article className="lf-soon">
      {illustration}
      <div className="lf-soon-top">
        <span className="lf-soon-icon" aria-hidden="true">
          <Icon name={icon} duotone size={32} />
        </span>
        <span className="lf-soon-badge">Bientôt</span>
      </div>
      <h3 className="lf-soon-title">{title}</h3>
      {tagline && <p className="lf-soon-tag">{tagline}</p>}
      {children && <p className="lf-soon-desc">{children}</p>}
    </article>
  );
}
