"use client";

// Les pages du Document, toutes, l'une sous l'autre, chargées à l'approche. On les agrandit pour lire une
// écriture serrée ; la page en vue est signalée au reste de l'écran, qui éclaire les volets qui la citent.
// Pour une photo de zone, on trace un rectangle sur une page (ou on règle ses bords au clavier).
// Les pages viennent du service relecture, même origine : le cookie de session les accompagne, et
// chaque ouverture est tracée.
import { Button, Icon } from "@lafia/design";
import { useEffect, useId, useRef, useState, type PointerEvent as EvenementDePointeur } from "react";

import { adresseDeLaPage, pluriel } from "../../../libelles";

export type Zone = [number, number, number, number];

/** Qui cite une page : pour aller de la page aux volets. */
export type Citation = { cle: string; libelle: string };

const ZOOMS = [1, 1.5, 2, 3];
const SEUILS = Array.from({ length: 11 }, (_, i) => i / 10);

function borne(n: number): number {
  return Math.min(1000, Math.max(0, Math.round(n)));
}

function mouvementReduit(): boolean {
  return typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** Le rectangle qu'on trace sur une page, en pour-mille de sa largeur et de sa hauteur. */
function Traceur({ page, zone, onTrace }: { page: number; zone: Zone | null; onTrace: (zone: Zone) => void }) {
  const depart = useRef<[number, number] | null>(null);

  function position(e: EvenementDePointeur<HTMLDivElement>): [number, number] {
    const cadre = e.currentTarget.getBoundingClientRect();
    return [borne(((e.clientX - cadre.left) / cadre.width) * 1000), borne(((e.clientY - cadre.top) / cadre.height) * 1000)];
  }
  function tracer(e: EvenementDePointeur<HTMLDivElement>) {
    if (!depart.current) return;
    const [x0, y0] = depart.current;
    const [x1, y1] = position(e);
    onTrace([Math.min(x0, x1), Math.min(y0, y1), Math.abs(x1 - x0), Math.abs(y1 - y0)]);
  }

  return (
    <div
      className="rel-traceur"
      aria-hidden="true"
      onPointerDown={(e) => {
        e.preventDefault();
        e.currentTarget.setPointerCapture(e.pointerId);
        depart.current = position(e);
        onTrace([...depart.current, 0, 0]);
      }}
      onPointerMove={tracer}
      onPointerUp={(e) => {
        tracer(e);
        depart.current = null;
      }}
      onPointerCancel={() => {
        depart.current = null;
      }}
    >
      {zone && zone[2] > 0 && zone[3] > 0 && (
        <span
          className="rel-traceur-zone"
          style={{ left: `${zone[0] / 10}%`, top: `${zone[1] / 10}%`, width: `${zone[2] / 10}%`, height: `${zone[3] / 10}%` }}
        >
          <span className="rel-masque">{`Zone de la page ${page}`}</span>
        </span>
      )}
    </div>
  );
}

/** Le choix d'une zone : tracée à la souris ou au doigt, ou réglée au clavier, en pour-mille. */
function ChoixDeZone({
  page,
  pages,
  zone,
  onPage,
  onZone,
  onInserer,
  onAnnuler,
}: {
  page: number;
  pages: number;
  zone: Zone | null;
  onPage: (page: number) => void;
  onZone: (zone: Zone) => void;
  onInserer: () => void;
  onAnnuler: () => void;
}) {
  const id = useId();
  const valeurs = zone ?? [0, 0, 0, 0];
  const champs: [string, number][] = [
    ["Gauche", 0],
    ["Haut", 1],
    ["Largeur", 2],
    ["Hauteur", 3],
  ];
  const prete = zone !== null && zone[2] >= 10 && zone[3] >= 10;
  const titre = useRef<HTMLHeadingElement>(null);
  useEffect(() => titre.current?.focus(), []);

  return (
    <section className="rel-choix-zone" aria-labelledby={`${id}-titre`}>
      <h3 className="rel-choix-zone-titre" id={`${id}-titre`} tabIndex={-1} ref={titre}>
        <Icon name="magnifying-glass" size={20} />
        <span>{`Photo d'une zone : tracez un rectangle sur la page ${page}`}</span>
      </h3>
      <p className="rel-meta">Ou réglez ses bords ci-dessous, en millièmes de la page (0 à 1000).</p>
      <div className="rel-choix-zone-champs">
        <label className="rel-champ-court">
          <span>Page</span>
          <input
            type="number"
            min={1}
            max={pages}
            value={page}
            onChange={(e) => onPage(Math.min(pages, Math.max(1, Number(e.target.value) || 1)))}
          />
        </label>
        {champs.map(([libelle, i]) => (
          <label key={libelle} className="rel-champ-court">
            <span>{libelle}</span>
            <input
              type="number"
              min={0}
              max={1000}
              step={10}
              value={valeurs[i]}
              onChange={(e) => {
                const suivante = [...valeurs] as Zone;
                suivante[i] = borne(Number(e.target.value) || 0);
                onZone(suivante);
              }}
            />
          </label>
        ))}
      </div>
      <div className="rel-actions">
        <Button size="pro" icon="plus" onClick={onInserer} disabled={!prete}>
          Insérer la zone
        </Button>
        <Button size="pro" variant="ghost" icon="x" onClick={onAnnuler}>
          Annuler
        </Button>
        {!prete && <span className="rel-meta">Tracez d'abord une zone d'au moins 10 millièmes de côté.</span>}
      </div>
    </section>
  );
}

export function Feuilles({
  tache,
  pages,
  formats = [],
  description,
  cible,
  citations,
  onPageEnVue,
  onVoirVolet,
  demandeDeZone,
  onZone,
  onAnnulerZone,
  gestesDePage,
}: {
  tache: string;
  pages: number;
  formats?: string[];
  description: string;
  /** Une page à montrer ; `n` change à chaque demande, même pour la même page. */
  cible?: { page: number; n: number } | null;
  /** Les volets qui citent chaque page. */
  citations?: Record<number, Citation[]>;
  onPageEnVue?: (page: number) => void;
  onVoirVolet?: (cle: string) => void;
  /** Le choix d'une zone en cours, pour une photo : la page proposée d'abord. */
  demandeDeZone?: { page: number } | null;
  onZone?: (page: number, zone: Zone) => void;
  onAnnulerZone?: () => void;
  /** Les gestes d'un clic sur la page en vue, à la Relecture : `voletActif` nomme le volet qui les reçoit. */
  gestesDePage?: {
    voletActif: string | null;
    onInsererPage: (page: number) => void;
    onZone: (page: number) => void;
    onNouveauVolet: (page: number) => void;
  };
}) {
  const total = Math.max(1, pages);
  const [zoom, setZoom] = useState(0);
  const [repliee, setRepliee] = useState(false);
  const [enPdf, setEnPdf] = useState<Record<number, boolean>>({});
  const [proportions, setProportions] = useState<Record<number, number>>({});
  const [enVue, setEnVue] = useState(1);
  const [rotation, setRotation] = useState(0);
  const [contraste, setContraste] = useState(false);
  const [trace, setTrace] = useState<{ page: number; zone: Zone | null }>({ page: 1, zone: null });
  const defilement = useRef<HTMLDivElement>(null);
  const enVueRef = useRef(1);
  const idDefilement = useId();

  /** Fait défiler le seul panneau des pages ; la fenêtre ne bouge que si le panneau est hors de vue (écran étroit). */
  function montrer(page: number, douce = true, panneauEnVue = false) {
    const racine = defilement.current;
    const feuille = document.getElementById(`feuille-${page}`);
    if (!racine || !feuille) return;
    const comportement = douce && !mouvementReduit() ? "smooth" : "auto";
    const haut = racine.scrollTop + feuille.getBoundingClientRect().top - racine.getBoundingClientRect().top - 8;
    racine.scrollTo({ top: haut, behavior: comportement });
    if (panneauEnVue) {
      const cadre = racine.getBoundingClientRect();
      if (cadre.bottom < 80 || cadre.top > window.innerHeight - 80) racine.scrollIntoView({ block: "nearest", behavior: comportement });
    }
  }
  const premierZoom = useRef(true);

  // Une page demandée par un volet : on déplie, puis on y va.
  useEffect(() => {
    if (!cible) return;
    setRepliee(false);
    setTimeout(() => montrer(cible.page, true, true), 0);
  }, [cible]);

  // Le choix d'une zone commence sur la page proposée.
  useEffect(() => {
    if (!demandeDeZone) return;
    setRepliee(false);
    setTrace({ page: demandeDeZone.page, zone: null });
    setTimeout(() => montrer(demandeDeZone.page, true, true), 0);
  }, [demandeDeZone]);

  // Après un changement de taille, la même page reste en vue.
  useEffect(() => {
    if (premierZoom.current) {
      premierZoom.current = false;
      return;
    }
    setTimeout(() => montrer(enVueRef.current, false), 0);
  }, [zoom]);

  // Ctrl + molette : agrandir ou réduire, sans zoomer toute la fenêtre.
  useEffect(() => {
    const racine = defilement.current;
    if (!racine) return;
    function molette(e: WheelEvent) {
      if (!e.ctrlKey) return;
      e.preventDefault();
      setZoom((z) => Math.min(ZOOMS.length - 1, Math.max(0, z + (e.deltaY < 0 ? 1 : -1))));
    }
    racine.addEventListener("wheel", molette, { passive: false });
    return () => racine.removeEventListener("wheel", molette);
  }, []);

  // La page la plus visible dans le panneau.
  useEffect(() => {
    const racine = defilement.current;
    if (!racine || repliee) return;
    const visibles = new Map<number, number>();
    const observateur = new IntersectionObserver(
      (entrees) => {
        for (const entree of entrees) {
          visibles.set(Number((entree.target as HTMLElement).dataset.page), entree.isIntersecting ? entree.intersectionRect.height : 0);
        }
        let meilleure = enVueRef.current;
        let hauteur = -1;
        for (const [page, h] of visibles) {
          if (h > hauteur) [meilleure, hauteur] = [page, h];
        }
        if (hauteur > 0 && meilleure !== enVueRef.current) {
          enVueRef.current = meilleure;
          setEnVue(meilleure);
          onPageEnVue?.(meilleure);
        }
      },
      { root: racine, threshold: SEUILS },
    );
    racine.querySelectorAll<HTMLElement>("[data-page]").forEach((feuille) => observateur.observe(feuille));
    return () => observateur.disconnect();
  }, [repliee, onPageEnVue, total]);

  const numeros = Array.from({ length: total }, (_, i) => i + 1);

  return (
    <section className={repliee ? "rel-feuilles is-repliee" : "rel-feuilles"} aria-label={`Pages du document : ${description}`}>
      <div className="rel-feuilles-barre">
        <p className="rel-feuilles-compte" aria-live="polite">
          <span>{`Page ${enVue}`}</span>
          <span className="rel-meta">{` sur ${total}`}</span>
        </p>
        <div className="rel-feuilles-zoom" role="group" aria-label="Taille des pages">
          <Button size="pro" variant="ghost" onClick={() => setZoom((z) => Math.max(0, z - 1))} disabled={zoom === 0}>
            − Réduire
          </Button>
          <span className="rel-chiffres rel-feuilles-taille" aria-live="polite">
            {zoom === 0 ? "Largeur" : `× ${String(ZOOMS[zoom]).replace(".", ",")}`}
          </span>
          <Button
            size="pro"
            variant="ghost"
            icon="magnifying-glass"
            onClick={() => setZoom((z) => Math.min(ZOOMS.length - 1, z + 1))}
            disabled={zoom === ZOOMS.length - 1}
          >
            Agrandir
          </Button>
        </div>
        <div className="rel-feuilles-lecture" role="group" aria-label="Lecture des pages">
          <button type="button" className="rel-geste" onClick={() => setRotation((r) => (r + 90) % 360)}>
            {rotation ? `Tourner (${rotation}°)` : "Tourner"}
          </button>
          <button type="button" className="rel-geste" aria-pressed={contraste} onClick={() => setContraste((c) => !c)}>
            Renforcer l'encre pâle
          </button>
        </div>
        <button
          type="button"
          className="lf-btn lf-btn--secondary lf-btn--pro rel-feuilles-replier"
          aria-expanded={!repliee}
          aria-controls={idDefilement}
          onClick={() => setRepliee((r) => !r)}
        >
          <Icon name={repliee ? "eye" : "caret-down"} size={20} />
          <span className="lf-btn-label">{repliee ? "Afficher les pages" : "Masquer les pages"}</span>
        </button>
      </div>

      {total > 1 && !repliee && (
        <nav className="rel-feuilles-sommaire" aria-label="Aller à la page">
          {numeros.map((numero) => (
            <button
              key={numero}
              type="button"
              className={numero === enVue ? "rel-feuilles-numero is-en-vue" : "rel-feuilles-numero"}
              aria-current={numero === enVue ? "page" : undefined}
              aria-label={`Page ${numero}`}
              onClick={() => montrer(numero)}
            >
              {numero}
            </button>
          ))}
        </nav>
      )}

      {gestesDePage && !demandeDeZone && !repliee && (
        <div className="rel-gestes-de-page" role="group" aria-label={`Gestes sur la page ${enVue}`}>
          <span className="rel-gestes-de-page-titre">{`Page ${enVue} :`}</span>
          <button
            type="button"
            className="rel-geste"
            disabled={!gestesDePage.voletActif}
            onClick={() => gestesDePage.onInsererPage(enVue)}
          >
            <Icon name="plus" size={16} /> Insérer cette page{gestesDePage.voletActif ? ` dans le ${gestesDePage.voletActif}` : ""}
          </button>
          <button
            type="button"
            className="rel-geste"
            disabled={!gestesDePage.voletActif || enPdf[enVue] || formats[enVue - 1] === "application/pdf"}
            onClick={() => gestesDePage.onZone(enVue)}
          >
            <Icon name="magnifying-glass" size={16} /> Sélectionner une zone
          </button>
          <button type="button" className="rel-geste" onClick={() => gestesDePage.onNouveauVolet(enVue)}>
            <Icon name="plus" size={16} /> Nouveau volet à partir de cette page
          </button>
          {!gestesDePage.voletActif && <span className="rel-meta">Choisissez d'abord un volet à droite pour y insérer la page.</span>}
        </div>
      )}

      {demandeDeZone && onZone && (
        <ChoixDeZone
          page={trace.page}
          pages={total}
          zone={trace.zone}
          onPage={(page) => {
            setTrace({ page, zone: null });
            montrer(page);
          }}
          onZone={(zone) => setTrace((t) => ({ ...t, zone }))}
          onInserer={() => trace.zone && onZone(trace.page, trace.zone)}
          onAnnuler={() => onAnnulerZone?.()}
        />
      )}

      <div className={contraste ? "rel-feuilles-defilement is-contraste" : "rel-feuilles-defilement"} id={idDefilement} ref={defilement} tabIndex={0} aria-label="Pages, défilables">
        <div className="rel-feuilles-piste" style={{ width: `${ZOOMS[zoom] * 100}%` }}>
          {numeros.map((numero) => {
            const src = adresseDeLaPage(tache, numero);
            const pdf = enPdf[numero] || formats[numero - 1] === "application/pdf";
            const cites = citations?.[numero] ?? [];
            const tracable = Boolean(demandeDeZone) && !pdf && rotation === 0;
            const proportion = proportions[numero] ?? 1 / Math.SQRT2;
            const couchee = rotation === 90 || rotation === 270;
            return (
              <figure
                key={numero}
                id={`feuille-${numero}`}
                data-page={numero}
                className={[
                  "rel-feuille",
                  numero === enVue && "is-en-vue",
                  tracable && "is-tracable",
                  tracable && trace.page === numero && "is-choisie",
                ]
                  .filter(Boolean)
                  .join(" ")}
              >
                <figcaption className="rel-feuille-legende">
                  <span className="rel-feuille-numero">{`Page ${numero}`}</span>
                  {cites.length > 0 ? (
                    <span className="rel-feuille-cites">
                      <span className="rel-meta">{`${pluriel(cites.length, "volet", "volets")} :`}</span>
                      {cites.map((c) =>
                        onVoirVolet ? (
                          <button key={c.cle} type="button" className="rel-lien-bouton" onClick={() => onVoirVolet(c.cle)}>
                            {c.libelle}
                          </button>
                        ) : (
                          <span key={c.cle}>{c.libelle}</span>
                        ),
                      )}
                    </span>
                  ) : (
                    citations && <span className="rel-meta">Citée par aucun volet</span>
                  )}
                  <a className="rel-feuille-onglet" href={src} target="_blank" rel="noopener">
                    <Icon name="arrow-square-out" size={18} />
                    <span>Nouvel onglet</span>
                  </a>
                </figcaption>
                <div
                  className="rel-feuille-cadre"
                  style={!pdf ? { aspectRatio: String(couchee ? 1 / proportion : proportion) } : undefined}
                >
                  {pdf ? (
                    <iframe className="rel-feuille-pdf" src={src} loading="lazy" title={`Page ${numero} sur ${total} : ${description}`} />
                  ) : (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={src}
                      alt={`Page ${numero} sur ${total} : ${description}`}
                      loading="lazy"
                      decoding="async"
                      draggable={false}
                      className={rotation ? "is-tournee" : undefined}
                      style={
                        rotation
                          ? couchee
                            ? { width: `${proportion * 100}%`, height: `${100 / proportion}%`, transform: `translate(-50%, -50%) rotate(${rotation}deg)` }
                            : { transform: `translate(-50%, -50%) rotate(${rotation}deg)` }
                          : undefined
                      }
                      onLoad={(e) => {
                        const image = e.currentTarget;
                        if (image.naturalWidth && image.naturalHeight) {
                          setProportions((deja) => ({ ...deja, [numero]: image.naturalWidth / image.naturalHeight }));
                        }
                      }}
                      onError={() => setEnPdf((deja) => ({ ...deja, [numero]: true }))}
                    />
                  )}
                  {tracable && (
                    <Traceur
                      page={numero}
                      zone={trace.page === numero ? trace.zone : null}
                      onTrace={(zone) => setTrace({ page: numero, zone })}
                    />
                  )}
                </div>
                {Boolean(demandeDeZone) && !pdf && rotation !== 0 && (
                  <p className="rel-meta">Remettez la page droite (Tourner) pour y tracer une zone.</p>
                )}
                {Boolean(demandeDeZone) && pdf && (
                  <p className="rel-meta">Page en PDF : on ne peut pas y tracer de zone. Insérez la page entière.</p>
                )}
              </figure>
            );
          })}
        </div>
      </div>
    </section>
  );
}
