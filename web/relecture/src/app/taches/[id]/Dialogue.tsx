"use client";

// Une fenêtre dans la page (jamais window.confirm) : le <dialog> natif, modal, qui garde le focus en son
// sein, se ferme à Échap, et rend le focus à ce qui l'a ouvert.
import { Icon } from "@lafia/design";
import { useEffect, useId, useRef, type ReactNode } from "react";

export function Dialogue({
  ouvert,
  titre,
  onFermer,
  children,
  pied,
  large,
}: {
  ouvert: boolean;
  titre: string;
  onFermer: () => void;
  children: ReactNode;
  pied: ReactNode;
  large?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const retour = useRef<HTMLElement | null>(null);
  const id = useId();

  useEffect(() => {
    const dialogue = ref.current;
    if (!dialogue) return;
    if (ouvert && !dialogue.open) {
      retour.current = document.activeElement as HTMLElement | null;
      dialogue.showModal();
      const premier = dialogue.querySelector<HTMLElement>("[data-focus-initial]") ?? dialogue.querySelector<HTMLElement>("h2");
      premier?.focus();
    }
    if (!ouvert && dialogue.open) {
      dialogue.close();
      retour.current?.focus();
    }
  }, [ouvert]);

  return (
    <dialog
      ref={ref}
      className={large ? "rel-dialogue rel-dialogue--large" : "rel-dialogue"}
      aria-labelledby={`${id}-titre`}
      onCancel={(e) => {
        e.preventDefault();
        onFermer();
      }}
    >
      <div className="rel-dialogue-tete">
        <h2 className="lf-app-sous-titre-fort" id={`${id}-titre`} tabIndex={-1}>
          {titre}
        </h2>
        <button type="button" className="rel-dialogue-fermer" onClick={onFermer} aria-label="Fermer">
          <Icon name="x" size={22} />
        </button>
      </div>
      <div className="rel-dialogue-corps">{children}</div>
      <div className="rel-dialogue-pied">{pied}</div>
    </dialog>
  );
}
