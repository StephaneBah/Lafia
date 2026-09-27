"use client";

// Les pages du Document, en grand : une à la fois, qu'on agrandit pour lire une écriture serrée. Une
// image s'affiche ; un PDF, que le navigateur ne dessine pas dans une image, s'ouvre dans un cadre et
// dans un nouvel onglet. Les pages viennent du service relecture, du même domaine : le cookie de
// session les accompagne, et chaque ouverture est tracée.
import { Button, Icon } from "@lafia/design";
import { useState } from "react";

import { adresseDeLaPage } from "../../../libelles";

const ZOOMS = [1, 1.5, 2, 3];

export function Pages({ tache, pages, description }: { tache: string; pages: number; description: string }) {
  const total = Math.max(1, pages);
  const [page, setPage] = useState(1);
  const [zoom, setZoom] = useState(0);
  const [enPdf, setEnPdf] = useState<Record<number, boolean>>({});
  const src = adresseDeLaPage(tache, page);

  function allerA(numero: number) {
    setPage(Math.min(total, Math.max(1, numero)));
    setZoom(0);
  }

  return (
    <section className="rel-pages" aria-label={`Pages du document : ${description}`}>
      <div className="rel-pages-barre">
        <p className="rel-pages-compte" aria-live="polite">
          {`Page ${page} sur ${total}`}
        </p>
        {!enPdf[page] && (
          <div className="rel-pages-zoom" role="group" aria-label="Taille de la page">
            <Button size="pro" variant="ghost" onClick={() => setZoom((z) => Math.max(0, z - 1))} disabled={zoom === 0}>
              − Réduire
            </Button>
            <span className="rel-chiffres" aria-live="polite">{zoom === 0 ? "Page entière" : `× ${String(ZOOMS[zoom]).replace(".", ",")}`}</span>
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
        )}
      </div>

      <div className="rel-page-cadre" tabIndex={0} aria-label={`Page ${page}, défilable quand elle est agrandie`}>
        {enPdf[page] ? (
          <iframe className="rel-page-pdf" src={src} title={`Page ${page} sur ${total} : ${description}`} />
        ) : (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            key={src}
            src={src}
            alt={`Page ${page} sur ${total} : ${description}`}
            className={zoom === 0 ? "rel-page-image is-entiere" : "rel-page-image"}
            style={zoom === 0 ? undefined : { width: `${ZOOMS[zoom] * 100}%` }}
            onError={() => setEnPdf((deja) => ({ ...deja, [page]: true }))}
          />
        )}
      </div>

      <div className="rel-pages-navigation">
        <Button size="pro" variant="secondary" icon="arrow-left" onClick={() => allerA(page - 1)} disabled={page === 1}>
          Page précédente
        </Button>
        <a className="rel-pages-onglet" href={src} target="_blank" rel="noopener">
          <Icon name="arrow-square-out" size={20} />
          <span>Ouvrir dans un nouvel onglet</span>
        </a>
        <Button size="pro" variant="secondary" onClick={() => allerA(page + 1)} disabled={page === total}>
          Page suivante
        </Button>
      </div>

      {total > 1 && (
        <ol className="rel-pages-liste" aria-label="Aller à la page">
          {Array.from({ length: total }, (_, i) => i + 1).map((numero) => (
            <li key={numero}>
              <button
                type="button"
                className={numero === page ? "rel-pages-numero is-courante" : "rel-pages-numero"}
                aria-current={numero === page ? "page" : undefined}
                aria-label={`Page ${numero}`}
                onClick={() => allerA(numero)}
              >
                {numero}
              </button>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
