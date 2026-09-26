"use client";

// « Un parcours, zéro ressaisie » : au défilement, le numéro d'ordonnance glisse le long du fil
// d'étape en étape, et chaque étape s'éveille quand il l'atteint. Horizontal dès 1024px, vertical en
// dessous. Sous mouvement réduit, toutes les étapes sont éveillées et le numéro ne voyage pas.

import { useEffect, useRef, type ReactNode } from "react";

export function Parcours({ numero, children }: { numero: string; children: ReactNode }) {
  const cadre = useRef<HTMLDivElement>(null);
  const liste = useRef<HTMLOListElement>(null);
  const puce = useRef<HTMLSpanElement>(null);
  const fil = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const wrap = cadre.current;
    const ol = liste.current;
    const chip = puce.current;
    const track = fil.current;
    if (!wrap || !ol || !chip || !track) return;
    const etapes = Array.from(ol.querySelectorAll<HTMLElement>(".jstep"));
    if (etapes.length === 0) return;
    const reduit = window.matchMedia("(prefers-reduced-motion: reduce)");
    let attendu = false;

    function placer() {
      attendu = false;
      if (!wrap || !chip || !track) return;
      const boite = wrap.getBoundingClientRect();
      const hauteur = window.innerHeight || 800;
      const horizontal = window.innerWidth >= 1024;
      // Vertical : le numéro suit la ligne de lecture, aux six dixièmes de l'écran. Horizontal : le
      // parcours est bas, le numéro voyage tant qu'il remonte du bas de l'écran jusqu'à son tiers haut.
      let avance = horizontal
        ? (hauteur * 0.8 - boite.top) / Math.max(1, boite.height + hauteur * 0.4)
        : (hauteur * 0.6 - boite.top) / Math.max(1, boite.height - hauteur * 0.2);
      avance = reduit.matches ? 1 : Math.max(0, Math.min(1, avance));
      const courante = Math.round(avance * (etapes.length - 1));
      etapes.forEach((etape, i) => etape.classList.toggle("is-awake", i <= courante));

      const premier = etapes[0].querySelector(".jnode")!.getBoundingClientRect();
      const dernier = etapes[etapes.length - 1].querySelector(".jnode")!.getBoundingClientRect();
      const ax = premier.left + premier.width / 2 - boite.left;
      const ay = premier.top + premier.height / 2 - boite.top;
      const zx = dernier.left + dernier.width / 2 - boite.left;
      const zy = dernier.top + dernier.height / 2 - boite.top;
      const largeur = chip.offsetWidth;
      const haut = chip.offsetHeight;
      if (horizontal) {
        track.style.cssText = `left:${ax}px;width:${zx - ax}px;top:${ay - 1}px;height:3px;right:auto;bottom:auto`;
        chip.style.transform = `translate(${ax - largeur / 2 + avance * (zx - ax)}px,${ay - haut - 18}px)`;
      } else {
        track.style.cssText = `top:${ay}px;height:${zy - ay}px;left:${ax - 1}px;width:3px;bottom:auto;right:auto`;
        chip.style.transform = `translate(${ax + 18}px,${ay - haut / 2 + avance * (zy - ay)}px)`;
      }
    }
    function demander() {
      if (!attendu) {
        attendu = true;
        requestAnimationFrame(placer);
      }
    }

    window.addEventListener("scroll", demander, { passive: true });
    window.addEventListener("resize", demander);
    reduit.addEventListener("change", demander);
    placer();
    document.fonts?.ready.then(demander);
    return () => {
      window.removeEventListener("scroll", demander);
      window.removeEventListener("resize", demander);
      reduit.removeEventListener("change", demander);
    };
  }, []);

  return (
    <div className="journey-wrap" ref={cadre}>
      <span className="journey-track" ref={fil} aria-hidden="true" />
      <span className="ord-chip" ref={puce} aria-hidden="true">
        {numero}
      </span>
      <ol className="journey" ref={liste}>
        {children}
      </ol>
    </div>
  );
}
