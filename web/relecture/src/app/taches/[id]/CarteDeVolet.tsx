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
import { Button, Icon, type NomIcone } from "@lafia/design";
import { useEffect, useId, useRef, useState } from "react";

import { adresseDeLaPage } from "../../../libelles";
import { enVolet, lirePages, normaliserDate, pagesEnTexte, type Meta, type VoletEdite } from "../../../edition";

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

/** Chaque type de volet avec son icône : le choix se fait d'un geste, pas dans une liste. */
export const ICONES_DES_VOLETS: Record<TypeDeVolet, NomIcone> = {
  consultation: "stethoscope",
  analyse: "test-tube",
  ordonnance: "pill",
  vaccination: "shield-check",
  hospitalisation: "hospital",
  imagerie: "eye",
  certificat: "identification-card",
  note: "list",
  illisible: "warning",
  autre: "info",
};

/** Les pages que cite un volet, en vignettes : un clic les montre à gauche. */
export function Vignettes({ tache, pages, onVoirPage }: { tache: string; pages: number[]; onVoirPage: (page: number) => void }) {
  if (!pages.length) return null;
  return (
    <ul className="rel-vignettes" aria-label="Pages citées">
      {pages.map((page) => (
        <li key={page}>
          <button type="button" className="rel-vignette" onClick={() => onVoirPage(page)} aria-label={`Voir la page ${page} à gauche`}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={adresseDeLaPage(tache, page)} alt="" loading="lazy" decoding="async" />
            <span className="rel-chiffres">{`p. ${page}`}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}

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
  suggestions,
}: {
  volet: VoletEdite;
  rang: number;
  pages: number;
  urlDePage: (n: number) => string;
  gestes: GestesDuVolet;
  photoOuverte: boolean;
  onPhoto: (ouverte: boolean) => void;
  suggestions: string[];
}) {
  const id = useId();
  const [date, setDate] = useState(volet.date ?? "");
  const [lieu, setLieu] = useState(volet.etablissement ?? "");
  const [pagesSaisies, setPagesSaisies] = useState(pagesEnTexte(volet.pages));
  const texte = useRef<HTMLTextAreaElement>(null);
  const typeChoisi = useRef<HTMLButtonElement>(null);
  useEffect(() => typeChoisi.current?.focus(), []);

  /** Les flèches passent d'un type à l'autre, comme dans tout groupe de boutons radio. */
  function flecheDeType(e: React.KeyboardEvent, i: number) {
    const pas = e.key === "ArrowRight" || e.key === "ArrowDown" ? 1 : e.key === "ArrowLeft" || e.key === "ArrowUp" ? -1 : 0;
    if (!pas) return;
    e.preventDefault();
    const suivant = TYPES_DE_VOLET[(i + pas + TYPES_DE_VOLET.length) % TYPES_DE_VOLET.length];
    gestes.onMeta({ type: suivant });
    const boutons = e.currentTarget.parentElement?.children;
    (boutons?.[TYPES_DE_VOLET.indexOf(suivant)] as HTMLElement | undefined)?.focus();
  }

  const dateLue = date.trim() ? normaliserDate(date) : null;
  const dateInvalide = date.trim() !== "" && dateLue === null;
  const lues = lirePages(pagesSaisies);
  const pagesInvalides = lues === null || lues.length === 0 || lues.some((p) => p < 1 || p > pages);

  function curseur() {
    if (texte.current) gestes.onCurseur(texte.current.selectionStart);
  }

  return (
    <div className="rel-formulaire">
      <div className="rel-formulaire-champs">
        <div className="rel-champ rel-types">
          <span className="rel-champ-libelle" id={`${id}-type`}>
            Type
          </span>
          <div className="rel-types-liste" role="radiogroup" aria-labelledby={`${id}-type`}>
            {TYPES_DE_VOLET.map((type, i) => (
              <button
                key={type}
                type="button"
                role="radio"
                ref={volet.type === type ? typeChoisi : undefined}
                className="rel-type"
                aria-checked={volet.type === type}
                tabIndex={volet.type === type ? 0 : -1}
                onClick={() => gestes.onMeta({ type })}
                onKeyDown={(e) => flecheDeType(e, i)}
              >
                <Icon name={ICONES_DES_VOLETS[type]} size={20} />
                <span>{LIBELLES_DES_VOLETS[type]}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="rel-champ">
          <label className="rel-champ-libelle" htmlFor={`${id}-date`}>
            Date
          </label>
          <input
            id={`${id}-date`}
            className="lf-input rel-chiffres"
            value={date}
            autoComplete="off"
            placeholder="14/03/2019"
            aria-invalid={dateInvalide || undefined}
            aria-describedby={`${id}-date-aide`}
            onChange={(e) => {
              setDate(e.target.value);
              const propre = e.target.value.trim();
              const lue = propre ? normaliserDate(propre) : null;
              if (!propre) gestes.onMeta({ date: null });
              else if (lue) gestes.onMeta({ date: lue });
            }}
            onBlur={() => dateLue && setDate(dateLue)}
          />
          <span id={`${id}-date-aide`} className={dateInvalide ? "rel-champ-aide is-erreur" : "rel-champ-aide"}>
            {dateInvalide ? (
              <>
                <Icon name="warning-octagon" size={16} />
                {" Pas encore une date : « 14/03/2019 », « mars 2019 », « 2019 »."}
              </>
            ) : dateLue ? (
              `Compris : ${dateEnLettres(dateLue)} (${dateLue})`
            ) : (
              "« 14/03/2019 », « mars 2019 » ou « 2019 ». Vide : date inconnue."
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
            list={`${id}-lieux`}
            aria-describedby={`${id}-lieu-aide`}
            onChange={(e) => {
              // « · » sépare les parties du titre : il ne peut pas être dans un nom.
              const propre = e.target.value.replace(/[·\n]/g, " ");
              setLieu(propre);
              gestes.onMeta({ etablissement: propre.trim() || null });
            }}
          />
          <datalist id={`${id}-lieux`}>
            {suggestions.map((nom) => (
              <option key={nom} value={nom} />
            ))}
          </datalist>
          <span id={`${id}-lieu-aide`} className="rel-champ-aide">
            Tel que la page l'écrit ; les noms déjà lus sont proposés. Vide : établissement inconnu.
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
  actif,
  attention,
  suggestions,
  onActiver,
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
  actif: boolean;
  attention: string[];
  suggestions: string[];
  onActiver: () => void;
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
      onFocus={onActiver}
      onPointerDown={onActiver}
      aria-current={actif ? "true" : undefined}
      className={[
        "rel-volet",
        volet.verifie && "is-verifie",
        enVue && "is-en-vue",
        enEdition && "is-en-edition",
        erreurs.length && "is-en-erreur",
        actif && "is-actif",
      ]
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
        {actif && (
          <span className="rel-marque rel-marque--actif">Volet actif</span>
        )}
        {attention.length > 0 && !volet.verifie && (
          <span className="rel-marque rel-marque--attention">
            <Icon name="warning" size={16} />
            <span>{`À regarder de près : ${attention.join(", ")}`}</span>
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

      <Vignettes tache={tache} pages={volet.pages} onVoirPage={gestes.onVoirPage} />

      {enEdition ? (
        <FormulaireDeVolet
          suggestions={suggestions}
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
