"use client";

// Un volet de la Transcription à la Relecture : rendu comme le liront le soignant et le citoyen, ou ouvert
// pour le corriger (type, date, établissement, pages, texte avec son aperçu), avec ses gestes (monter,
// descendre, couper au curseur, fusionner avec le suivant, supprimer, insérer une photo de page) et la
// coche « Vérifié contre les pages ».
import {
  LIBELLES_DES_VOLETS,
  RenduDeVolet,
  TYPES_DE_VOLET,
  dateEnLettres,
  type TypeDeVolet,
} from "@lafia/commun/transcription";
import { Button, Icon } from "@lafia/design";
import { useEffect, useId, useRef, useState } from "react";

import { adresseDeLaPage } from "../../../libelles";
import { FORMAT_DE_DATE, enVolet, lirePages, pagesEnTexte, type Meta, type VoletEdite } from "../../../edition";

export type GestesDuVolet = {
  onMeta: (meta: Partial<Meta>) => void;
  onCorps: (corps: string) => void;
  onCurseur: (position: number) => void;
  onEditer: (ouvert: boolean) => void;
  onMonter: () => void;
  onDescendre: () => void;
  onCouper: (position: number) => void;
  onFusionner: () => void;
  onSupprimer: () => void;
  onVerifier: (verifie: boolean) => void;
  onVoirPage: (page: number) => void;
  onPhotoEntiere: (page: number, legende: string) => void;
  onPhotoZone: (page: number, legende: string) => void;
};

function PhotoDePage({
  pages,
  proposees,
  onEntiere,
  onZone,
  onFermer,
}: {
  pages: number;
  proposees: number[];
  onEntiere: (page: number, legende: string) => void;
  onZone: (page: number, legende: string) => void;
  onFermer: () => void;
}) {
  const id = useId();
  const [page, setPage] = useState(proposees[0] ?? 1);
  const [legende, setLegende] = useState("");
  const premier = useRef<HTMLSelectElement>(null);
  useEffect(() => premier.current?.focus(), []);

  return (
    <fieldset className="rel-photo">
      <legend className="rel-photo-titre">Insérer une photo de la page</legend>
      <p className="rel-meta">
        La photo n'est pas copiée : la Transcription renvoie à la page du Document, entière ou une zone.
      </p>
      <div className="rel-photo-champs">
        <label className="rel-champ" htmlFor={`${id}-page`}>
          <span className="rel-champ-libelle">Page</span>
          <select id={`${id}-page`} ref={premier} className="lf-input rel-select" value={page} onChange={(e) => setPage(Number(e.target.value))}>
            {Array.from({ length: pages }, (_, i) => i + 1).map((n) => (
              <option key={n} value={n}>
                {`Page ${n}${proposees.includes(n) ? " (de ce volet)" : ""}`}
              </option>
            ))}
          </select>
        </label>
        <label className="rel-champ rel-champ--large" htmlFor={`${id}-legende`}>
          <span className="rel-champ-libelle">Légende (facultatif)</span>
          <input
            id={`${id}-legende`}
            className="lf-input"
            value={legende}
            onChange={(e) => setLegende(e.target.value)}
            placeholder="Feuille de résultats"
            autoComplete="off"
          />
        </label>
      </div>
      <div className="rel-actions">
        <Button size="pro" variant="secondary" icon="plus" onClick={() => onEntiere(page, legende)}>
          La page entière
        </Button>
        <Button size="pro" variant="secondary" icon="magnifying-glass" onClick={() => onZone(page, legende)}>
          Une zone de la page…
        </Button>
        <Button size="pro" variant="ghost" icon="x" onClick={onFermer}>
          Fermer
        </Button>
      </div>
    </fieldset>
  );
}

/** Le volet ouvert : ses champs, son texte en Markdown, son aperçu. */
function FormulaireDeVolet({
  volet,
  rang,
  pages,
  urlDePage,
  gestes,
  photoOuverte,
  onPhoto,
}: {
  volet: VoletEdite;
  rang: number;
  pages: number;
  urlDePage: (n: number) => string;
  gestes: GestesDuVolet;
  photoOuverte: boolean;
  onPhoto: (ouverte: boolean) => void;
}) {
  const id = useId();
  const [date, setDate] = useState(volet.date ?? "");
  const [lieu, setLieu] = useState(volet.etablissement ?? "");
  const [pagesSaisies, setPagesSaisies] = useState(pagesEnTexte(volet.pages));
  const texte = useRef<HTMLTextAreaElement>(null);
  const premier = useRef<HTMLSelectElement>(null);
  useEffect(() => premier.current?.focus(), []);

  const dateInvalide = date.trim() !== "" && !FORMAT_DE_DATE.test(date.trim());
  const lues = lirePages(pagesSaisies);
  const pagesInvalides = lues === null || lues.length === 0 || lues.some((p) => p < 1 || p > pages);

  function curseur() {
    if (texte.current) gestes.onCurseur(texte.current.selectionStart);
  }

  return (
    <div className="rel-formulaire">
      <div className="rel-formulaire-champs">
        <label className="rel-champ" htmlFor={`${id}-type`}>
          <span className="rel-champ-libelle">Type</span>
          <select
            id={`${id}-type`}
            ref={premier}
            className="lf-input rel-select"
            value={volet.type}
            onChange={(e) => gestes.onMeta({ type: e.target.value as TypeDeVolet })}
          >
            {TYPES_DE_VOLET.map((type) => (
              <option key={type} value={type}>
                {LIBELLES_DES_VOLETS[type]}
              </option>
            ))}
          </select>
        </label>

        <div className="rel-champ">
          <label className="rel-champ-libelle" htmlFor={`${id}-date`}>
            Date
          </label>
          <input
            id={`${id}-date`}
            className="lf-input rel-chiffres"
            value={date}
            inputMode="numeric"
            autoComplete="off"
            placeholder="AAAA-MM-JJ"
            aria-invalid={dateInvalide || undefined}
            aria-describedby={`${id}-date-aide`}
            onChange={(e) => {
              setDate(e.target.value);
              const propre = e.target.value.trim();
              if (!propre) gestes.onMeta({ date: null });
              else if (FORMAT_DE_DATE.test(propre)) gestes.onMeta({ date: propre });
            }}
          />
          <span id={`${id}-date-aide`} className={dateInvalide ? "rel-champ-aide is-erreur" : "rel-champ-aide"}>
            {dateInvalide ? (
              <>
                <Icon name="warning-octagon" size={16} />
                {" Pas encore une date : AAAA, AAAA-MM ou AAAA-MM-JJ."}
              </>
            ) : date.trim() ? (
              dateEnLettres(date.trim())
            ) : (
              "AAAA, AAAA-MM ou AAAA-MM-JJ. Vide : date inconnue."
            )}
          </span>
        </div>

        <div className="rel-champ rel-champ--large">
          <label className="rel-champ-libelle" htmlFor={`${id}-lieu`}>
            Établissement
          </label>
          <input
            id={`${id}-lieu`}
            className="lf-input"
            value={lieu}
            autoComplete="off"
            aria-describedby={`${id}-lieu-aide`}
            onChange={(e) => {
              // « · » sépare les parties du titre : il ne peut pas être dans un nom.
              const propre = e.target.value.replace(/[·\n]/g, " ");
              setLieu(propre);
              gestes.onMeta({ etablissement: propre.trim() || null });
            }}
          />
          <span id={`${id}-lieu-aide`} className="rel-champ-aide">
            Tel que la page l'écrit. Vide : établissement inconnu.
          </span>
        </div>

        <div className="rel-champ">
          <label className="rel-champ-libelle" htmlFor={`${id}-pages`}>
            Pages
          </label>
          <input
            id={`${id}-pages`}
            className="lf-input rel-chiffres"
            value={pagesSaisies}
            autoComplete="off"
            aria-invalid={pagesInvalides || undefined}
            aria-describedby={`${id}-pages-aide`}
            onChange={(e) => {
              setPagesSaisies(e.target.value);
              const lues = lirePages(e.target.value);
              if (lues && lues.length && lues.every((p) => p >= 1 && p <= pages)) gestes.onMeta({ pages: lues });
            }}
          />
          <span id={`${id}-pages-aide`} className={pagesInvalides ? "rel-champ-aide is-erreur" : "rel-champ-aide"}>
            {pagesInvalides ? (
              <>
                <Icon name="warning-octagon" size={16} />
                {` Des pages de 1 à ${pages}, comme « 3-4, 6 ».`}
              </>
            ) : (
              `Comme « 3-4, 6 ». Le document en a ${pages}.`
            )}
          </span>
        </div>
      </div>

      <div className="rel-champ">
        <div className="rel-texte-barre">
          <label className="rel-champ-libelle" htmlFor={`${id}-corps`}>
            Texte du volet
          </label>
          <div className="rel-actions">
            <Button size="pro" variant="ghost" icon="plus" onClick={() => onPhoto(!photoOuverte)} aria-expanded={photoOuverte}>
              Insérer une photo de la page
            </Button>
            <Button
              size="pro"
              variant="ghost"
              onClick={() => gestes.onCouper(texte.current?.selectionStart ?? volet.corps.length)}
              aria-describedby={`${id}-couper-aide`}
            >
              ✂ Couper au curseur
            </Button>
          </div>
        </div>
        <span id={`${id}-couper-aide`} className="rel-masque">
          La suite du texte, à partir du curseur, devient un volet neuf juste après celui-ci.
        </span>
        {photoOuverte && (
          <PhotoDePage
            pages={pages}
            proposees={volet.pages}
            onEntiere={(page, legende) => {
              gestes.onPhotoEntiere(page, legende);
              onPhoto(false);
            }}
            onZone={(page, legende) => gestes.onPhotoZone(page, legende)}
            onFermer={() => onPhoto(false)}
          />
        )}
        <textarea
          id={`${id}-corps`}
          ref={texte}
          className="lf-input rel-corps"
          value={volet.corps}
          rows={Math.min(24, Math.max(8, volet.corps.split("\n").length + 2))}
          spellCheck={false}
          aria-describedby={`${id}-corps-aide`}
          onChange={(e) => {
            gestes.onCorps(e.target.value);
            gestes.onCurseur(e.target.selectionStart);
          }}
          onSelect={curseur}
          onKeyUp={curseur}
          onClick={curseur}
        />
        <span id={`${id}-corps-aide`} className="rel-champ-aide">
          Markdown restreint : **gras**, *italique*, listes « - », tableaux « | », sous-titres « ### ».
        </span>
      </div>

      <div className="rel-apercu">
        <p className="rel-apercu-titre">Aperçu</p>
        <RenduDeVolet volet={enVolet(volet, rang)} urlDePage={urlDePage} surPage={gestes.onVoirPage} />
      </div>
    </div>
  );
}

export function CarteDeVolet({
  tache,
  volet,
  rang,
  total,
  pages,
  enEdition,
  pageEnVue,
  erreurs,
  gestes,
}: {
  tache: string;
  volet: VoletEdite;
  rang: number;
  total: number;
  pages: number;
  enEdition: boolean;
  pageEnVue: number;
  erreurs: string[];
  gestes: GestesDuVolet;
}) {
  const [photoOuverte, setPhotoOuverte] = useState(false);
  const enVue = volet.pages.includes(pageEnVue);
  const urlDePage = (n: number) => adresseDeLaPage(tache, n);
  const numero = rang + 1;
  const nom = `volet ${numero}`;

  return (
    <li
      id={`volet-${volet.cle}`}
      tabIndex={-1}
      className={["rel-volet", volet.verifie && "is-verifie", enVue && "is-en-vue", enEdition && "is-en-edition", erreurs.length && "is-en-erreur"]
        .filter(Boolean)
        .join(" ")}
    >
      <div className="rel-volet-outils">
        <span className="rel-volet-rang rel-chiffres">{`Volet ${numero} / ${total}`}</span>
        {enVue && (
          <span className="rel-marque rel-marque--vue">
            <Icon name="eye" size={16} />
            <span>{`page ${pageEnVue} en vue`}</span>
          </span>
        )}
        {volet.verifie && (
          <span className="rel-marque rel-marque--verifie">
            <Icon name="check" size={16} />
            <span>Vérifié</span>
          </span>
        )}
        <span className="rel-volet-gestes">
          <Button
            id={`editer-${volet.cle}`}
            size="pro"
            variant={enEdition ? "primary" : "secondary"}
            icon={enEdition ? "check" : undefined}
            onClick={() => gestes.onEditer(!enEdition)}
            aria-expanded={enEdition}
            aria-label={enEdition ? `Terminer la modification du ${nom}` : `Modifier le ${nom}`}
          >
            {enEdition ? "Terminer" : "Modifier"}
          </Button>
          <button
            id={`monter-${volet.cle}`}
            type="button"
            className="rel-geste"
            onClick={gestes.onMonter}
            disabled={rang === 0}
            aria-label={`Monter le ${nom}`}
          >
            <span aria-hidden="true">↑</span> Monter
          </button>
          <button
            id={`descendre-${volet.cle}`}
            type="button"
            className="rel-geste"
            onClick={gestes.onDescendre}
            disabled={rang === total - 1}
            aria-label={`Descendre le ${nom}`}
          >
            <span aria-hidden="true">↓</span> Descendre
          </button>
          <button
            type="button"
            className="rel-geste"
            onClick={gestes.onFusionner}
            disabled={rang === total - 1}
            aria-label={`Fusionner le ${nom} avec le suivant`}
          >
            <span aria-hidden="true">⤓</span> Fusionner avec le suivant
          </button>
          <button type="button" className="rel-geste rel-geste--danger" onClick={gestes.onSupprimer} aria-label={`Supprimer le ${nom}`}>
            <Icon name="x" size={16} /> Supprimer
          </button>
        </span>
      </div>

      {erreurs.length > 0 && (
        <ul className="rel-volet-erreurs" aria-label={`À reprendre dans le ${nom}`}>
          {erreurs.map((e) => (
            <li key={e}>
              <Icon name="warning-octagon" size={16} />
              <span>{e}</span>
            </li>
          ))}
        </ul>
      )}

      {enEdition ? (
        <FormulaireDeVolet
          volet={volet}
          rang={rang}
          pages={pages}
          urlDePage={urlDePage}
          gestes={gestes}
          photoOuverte={photoOuverte}
          onPhoto={setPhotoOuverte}
        />
      ) : (
        <RenduDeVolet volet={enVolet(volet, rang)} urlDePage={urlDePage} surPage={gestes.onVoirPage} />
      )}

      <label className="rel-verifie">
        <input type="checkbox" checked={volet.verifie} onChange={(e) => gestes.onVerifier(e.target.checked)} />
        <span>
          <strong>Vérifié contre les pages</strong>
          <span className="rel-meta">
            {volet.pages.length
              ? ` : j'ai relu ce volet contre ${volet.pages.length > 1 ? `les pages ${pagesEnTexte(volet.pages)}` : `la page ${volet.pages[0]}`}.`
              : " : ce volet ne cite encore aucune page."}
          </span>
        </span>
      </label>
    </li>
  );
}
