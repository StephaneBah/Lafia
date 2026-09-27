"use client";

// La première page d'un Document. Une image s'affiche ; un PDF, que le navigateur ne dessine pas dans
// une image, devient une vignette nommée qui l'ouvre à côté.
import { Icon } from "@lafia/design";
import { useState } from "react";

export function Vignette({ src, alt }: { src: string; alt: string }) {
  const [illisible, setIllisible] = useState(false);
  if (illisible) {
    return (
      <a className="num-vignette num-vignette--pdf" href={src} target="_blank" rel="noopener">
        <Icon name="arrow-square-out" size={24} />
        <span>Ouvrir la page</span>
      </a>
    );
  }
  // eslint-disable-next-line @next/next/no-img-element
  return <img className="num-vignette" src={src} alt={alt} loading="lazy" onError={() => setIllisible(true)} />;
}
