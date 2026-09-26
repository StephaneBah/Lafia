"use client";

import { useState } from "react";

import { Button } from "./Button";
import { Icon } from "./Icon";
import { Logo } from "./Logo";
import { cx } from "./svg";

const SECTIONS = [
  { label: "Vision", href: "#vision" },
  { label: "Comment ça marche", href: "#comment" },
  { label: "Services", href: "#services" },
  { label: "Demain", href: "#demain" },
];

/** En-tête du site produit : le logo, les sections, et la porte du citoyen « Ouvrir mon carnet ». */
export function SiteHeader({
  links = SECTIONS,
  ctaHref,
  ctaLabel = "Ouvrir mon carnet",
  homeHref = "#top",
  sticky = true,
  animateLogo = false,
}: {
  links?: Array<{ label: string; href: string }>;
  ctaHref: string;
  ctaLabel?: string;
  homeHref?: string;
  sticky?: boolean;
  animateLogo?: boolean;
}) {
  const [ouvert, setOuvert] = useState(false);
  return (
    <header className={cx("lf-siteheader", sticky && "is-sticky")}>
      <div className="lf-siteheader-in">
        <Logo height={32} href={homeHref} linkLabel="Lafia, haut de page" animate={animateLogo} />
        <nav
          className={cx("lf-siteheader-nav", ouvert && "is-open")}
          id="lf-nav"
          aria-label="Sections"
          onClick={(e) => {
            if ((e.target as HTMLElement).closest("a")) setOuvert(false);
          }}
        >
          {links.map((lien) => (
            <a key={lien.href} href={lien.href}>
              {lien.label}
            </a>
          ))}
        </nav>
        <Button href={ctaHref} icon="identification-card" className="lf-siteheader-cta">
          {ctaLabel}
        </Button>
        <button
          type="button"
          className="lf-iconbtn lf-siteheader-menu"
          aria-expanded={ouvert}
          aria-controls="lf-nav"
          onClick={() => setOuvert(!ouvert)}
        >
          <Icon name={ouvert ? "x" : "list"} size={24} label="Menu" />
        </button>
      </div>
    </header>
  );
}
