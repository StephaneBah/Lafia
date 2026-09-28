// Lire et montrer une Transcription (ADR 0010), le Markdown restreint des documents anciens relus.
//
// Le rendu n'accepte que le sous-ensemble de l'ADR : titres de volet, paragraphes, gras, italique,
// listes, tableaux, images `page:N` ou `page:N#x,y,l,h`. Tout texte est échappé par React : aucun HTML
// n'est jamais injecté, quoi qu'écrivent la machine ou les relecteurs. Une image ne résout que vers la
// route de page que l'application fournit. Le même module sert relecture, soin et le carnet.
//
// Importé par un sous-chemin, "@lafia/commun/transcription" : il n'embarque rien du serveur.

import type { ReactNode } from "react";

export const TYPES_DE_VOLET = [
  "consultation",
  "analyse",
  "ordonnance",
  "vaccination",
  "hospitalisation",
  "imagerie",
  "certificat",
  "note",
  "illisible",
  "autre",
] as const;
export type TypeDeVolet = (typeof TYPES_DE_VOLET)[number];

export const LIBELLES_DES_VOLETS: Record<TypeDeVolet, string> = {
  consultation: "Consultation",
  analyse: "Analyse",
  ordonnance: "Ordonnance",
  vaccination: "Vaccination",
  hospitalisation: "Hospitalisation",
  imagerie: "Imagerie",
  certificat: "Certificat",
  note: "Note",
  illisible: "Passage illisible",
  autre: "Autre",
};

export type Volet = {
  titre: string;
  type: TypeDeVolet;
  /** `AAAA`, `AAAA-MM` ou `AAAA-MM-JJ` ; null quand le papier ne la donne pas. */
  date: string | null;
  etablissement: string | null;
  pages: number[];
  corps: string;
  /** La place du volet dans la Transcription. */
  rang: number;
};

export type Transcription = {
  etablissements: string[];
  periode: string | null;
  volets: Volet[];
  /** Ce qui ne suit pas le format ; jamais bloquant pour lire, bloquant pour confirmer. */
  erreurs: string[];
};

const TITRE = /^##\s+([^·\n]+?)\s*·\s*([^·\n]+?)\s*·\s*([^·\n]+?)\s*·\s*p\.\s*([0-9 ,\-–]+)\s*$/;
const DATE = /^\d{4}(-\d{2}(-\d{2})?)?$/;
const IMAGE = /!\[([^\]]*)\]\(page:(\d+)(?:#(\d+),(\d+),(\d+),(\d+))?\)/g;

function lesPages(texte: string): number[] {
  const pages: number[] = [];
  for (const morceau of texte.split(",").map((m) => m.trim()).filter(Boolean)) {
    const bornes = morceau.split(/\s*[-–]\s*/);
    if (bornes.length === 2 && /^\d+$/.test(bornes[0]) && /^\d+$/.test(bornes[1])) {
      const [a, b] = [Number(bornes[0]), Number(bornes[1])];
      for (let p = Math.min(a, b); p <= Math.max(a, b); p++) pages.push(p);
    } else if (/^\d+$/.test(morceau)) pages.push(Number(morceau));
  }
  return [...new Set(pages)];
}

/** La structure d'une Transcription. `pagesDuDocument` signale les renvois hors du Document. */
export function lireTranscription(markdown: string, pagesDuDocument?: number): Transcription {
  const lignes = markdown.replace(/\r\n/g, "\n").split("\n");
  let etablissements: string[] = [];
  let periode: string | null = null;
  const erreurs: string[] = [];
  let debut = 0;
  if (lignes[0]?.trim() === "---") {
    const fin = lignes.findIndex((l, i) => i > 0 && l.trim() === "---");
    if (fin > 0) {
      for (const ligne of lignes.slice(1, fin)) {
        const [cle, ...reste] = ligne.split(":");
        const valeur = reste.join(":").trim();
        if (cle.trim() === "etablissements") etablissements = valeur.split(";").map((e) => e.trim()).filter(Boolean);
        if (cle.trim() === "periode") periode = valeur || null;
      }
      debut = fin + 1;
    }
  }
  const volets: Volet[] = [];
  let courant: Omit<Volet, "corps" | "rang"> | null = null;
  let corps: string[] = [];
  const clore = () => {
    if (courant) volets.push({ ...courant, corps: corps.join("\n").trim(), rang: volets.length });
  };
  lignes.slice(debut).forEach((ligne, i) => {
    const numero = debut + i + 1;
    if (ligne.startsWith("## ")) {
      clore();
      corps = [];
      const t = TITRE.exec(ligne.trim());
      if (!t) {
        erreurs.push(`ligne ${numero} : titre de volet hors format`);
        courant = { titre: ligne.slice(3).trim(), type: "autre", date: null, etablissement: null, pages: [] };
        return;
      }
      let type = t[1].trim().toLowerCase() as TypeDeVolet;
      if (!TYPES_DE_VOLET.includes(type)) {
        erreurs.push(`ligne ${numero} : type de volet inconnu « ${type} »`);
        type = "autre";
      }
      let date: string | null = t[2].trim();
      if (date === "?") date = null;
      else if (!DATE.test(date)) {
        erreurs.push(`ligne ${numero} : date « ${date} » hors format`);
        date = null;
      }
      const pages = lesPages(t[4]);
      if (pagesDuDocument && pages.some((p) => p < 1 || p > pagesDuDocument)) {
        erreurs.push(`ligne ${numero} : page hors du document`);
      }
      const etablissement = t[3].trim() === "?" ? null : t[3].trim();
      courant = { titre: ligne.slice(3).trim(), type, date, etablissement, pages };
    } else if (courant) {
      corps.push(ligne);
      for (const image of ligne.matchAll(IMAGE)) {
        const n = Number(image[2]);
        if (pagesDuDocument && (n < 1 || n > pagesDuDocument)) erreurs.push(`ligne ${numero} : image d'une page hors du document`);
      }
    }
  });
  clore();
  return { etablissements, periode, volets, erreurs };
}

/** Le titre d'un volet, tel que l'ADR 0010 l'écrit. */
export function titreDeVolet(v: Pick<Volet, "type" | "date" | "etablissement" | "pages">): string {
  const pages = v.pages.length > 1 && v.pages.every((p, i) => i === 0 || p === v.pages[i - 1] + 1)
    ? `${v.pages[0]}-${v.pages[v.pages.length - 1]}`
    : v.pages.join(", ");
  return `## ${v.type} · ${v.date ?? "?"} · ${v.etablissement ?? "?"} · p. ${pages || "?"}`;
}

/** Les volets en ordre de date ; un volet sans date garde sa place après le volet daté qui le précède. */
export function parDate(volets: Volet[]): Volet[] {
  let derniere = "";
  return volets
    .map((v, rang) => {
      if (v.date) derniere = v.date;
      return { v, cle: v.date ?? derniere, sansDate: v.date ? 0 : 1, rang };
    })
    .sort((a, b) => (a.cle < b.cle ? -1 : a.cle > b.cle ? 1 : a.sansDate - b.sansDate || a.rang - b.rang))
    .map((x) => x.v);
}

export const SANS_ETABLISSEMENT = "Établissement non précisé";

/** Les volets regroupés par établissement, chacun en ordre de date. */
export function parEtablissement(volets: Volet[]): [string, Volet[]][] {
  const groupes = new Map<string, Volet[]>();
  for (const v of volets) {
    const cle = v.etablissement ?? SANS_ETABLISSEMENT;
    groupes.set(cle, [...(groupes.get(cle) ?? []), v]);
  }
  return [...groupes.entries()].sort(([a], [b]) => a.localeCompare(b, "fr")).map(([nom, liste]) => [nom, parDate(liste)]);
}

/** Une date de volet en toutes lettres : « 14 mars 2019 », « mars 2019 », « 2019 », « Date inconnue ». */
export function dateEnLettres(date: string | null): string {
  if (!date) return "Date inconnue";
  const [a, m, j] = date.split("-").map(Number);
  const mois = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"];
  if (j) return `${j} ${mois[m - 1]} ${a}`;
  if (m) return `${mois[m - 1]} ${a}`;
  return String(a);
}

// ---- Rendu ----

type Contexte = {
  /** L'adresse d'une page du Document, servie par le service de l'application. */
  urlDePage: (numero: number) => string;
  /** Appelé quand on touche une image : l'application peut montrer la page dans son visionneur. */
  surPage?: (numero: number) => void;
};

function enLigne(texte: string, ctx: Contexte, cle: string): ReactNode[] {
  // Images d'abord, puis gras et italique ; tout le reste reste du texte, échappé par React.
  const morceaux: ReactNode[] = [];
  let dernier = 0;
  let i = 0;
  for (const m of texte.matchAll(IMAGE)) {
    if (m.index! > dernier) morceaux.push(...emphase(texte.slice(dernier, m.index), `${cle}-t${i}`));
    morceaux.push(<ImageDePage key={`${cle}-i${i}`} legende={m[1]} page={Number(m[2])} zone={m[3] ? [m[3], m[4], m[5], m[6]].map(Number) as [number, number, number, number] : undefined} ctx={ctx} />);
    dernier = m.index! + m[0].length;
    i++;
  }
  morceaux.push(...emphase(texte.slice(dernier), `${cle}-f`));
  return morceaux;
}

function emphase(texte: string, cle: string): ReactNode[] {
  const parties = texte.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g);
  return parties.map((p, i) => {
    if (/^\*\*[^*]+\*\*$/.test(p)) return <strong key={`${cle}-${i}`}>{p.slice(2, -2)}</strong>;
    if (/^\*[^*]+\*$/.test(p)) return <em key={`${cle}-${i}`}>{p.slice(1, -1)}</em>;
    return p;
  });
}

const PROPORTION_DE_PAGE = Math.SQRT2;

function ImageDePage({ legende, page, zone, ctx }: { legende: string; page: number; zone?: [number, number, number, number]; ctx: Contexte }) {
  const src = ctx.urlDePage(page);
  const contenu = zone ? (
    // Une zone de la page, en pour-mille : la page entière, agrandie et décalée dans un cadre.
    <span
      className="lf-transcription-zone"
      // Une page de carnet est en portrait, proche de l'A4 (hauteur ≈ √2 × largeur) : le cadre en tient compte.
      style={{ aspectRatio: `${zone[2]} / ${zone[3] * PROPORTION_DE_PAGE}` }}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt={legende || `Page ${page}`}
        style={{
          width: `${(1000 / zone[2]) * 100}%`,
          left: `${(-zone[0] / zone[2]) * 100}%`,
          top: `${(-zone[1] / zone[3]) * 100}%`,
        }}
      />
    </span>
  ) : (
    // eslint-disable-next-line @next/next/no-img-element
    <img className="lf-transcription-page" src={src} alt={legende || `Page ${page}`} />
  );
  return (
    <figure className="lf-transcription-figure">
      {ctx.surPage ? (
        <button type="button" className="lf-transcription-voir" onClick={() => ctx.surPage?.(page)}>
          {contenu}
        </button>
      ) : (
        contenu
      )}
      <figcaption>
        {legende ? `${legende} · ` : ""}page {page}
      </figcaption>
    </figure>
  );
}

function blocs(corps: string, ctx: Contexte, cle: string): ReactNode[] {
  const lignes = corps.split("\n");
  const sortie: ReactNode[] = [];
  let i = 0;
  while (i < lignes.length) {
    const ligne = lignes[i];
    if (!ligne.trim()) {
      i++;
      continue;
    }
    if (ligne.trim().startsWith("|")) {
      const tableau: string[] = [];
      while (i < lignes.length && lignes[i].trim().startsWith("|")) tableau.push(lignes[i++].trim());
      const cellules = (l: string) => l.replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
      const [entete, ...reste] = tableau;
      const corpsDuTableau = reste.filter((l) => !/^\|?\s*:?-{2,}/.test(l));
      sortie.push(
        <div className="lf-transcription-tableau" key={`${cle}-tab${i}`}>
          <table>
            <thead>
              <tr>{cellules(entete).map((c, j) => <th key={j}>{enLigne(c, ctx, `${cle}-h${i}-${j}`)}</th>)}</tr>
            </thead>
            <tbody>
              {corpsDuTableau.map((l, k) => (
                <tr key={k}>{cellules(l).map((c, j) => <td key={j}>{enLigne(c, ctx, `${cle}-c${i}-${k}-${j}`)}</td>)}</tr>
              ))}
            </tbody>
          </table>
        </div>,
      );
      continue;
    }
    if (/^\s*[-*]\s+/.test(ligne)) {
      const items: string[] = [];
      while (i < lignes.length && /^\s*[-*]\s+/.test(lignes[i])) items.push(lignes[i++].replace(/^\s*[-*]\s+/, ""));
      sortie.push(
        <ul key={`${cle}-ul${i}`}>{items.map((it, j) => <li key={j}>{enLigne(it, ctx, `${cle}-li${i}-${j}`)}</li>)}</ul>,
      );
      continue;
    }
    if (/^###\s+/.test(ligne)) {
      sortie.push(<h4 key={`${cle}-h${i}`}>{enLigne(ligne.replace(/^###\s+/, ""), ctx, `${cle}-h${i}`)}</h4>);
      i++;
      continue;
    }
    const paragraphe: string[] = [];
    while (i < lignes.length && lignes[i].trim() && !lignes[i].trim().startsWith("|") && !/^\s*[-*]\s+/.test(lignes[i]) && !/^###\s+/.test(lignes[i])) {
      paragraphe.push(lignes[i++]);
    }
    sortie.push(<p key={`${cle}-p${i}`}>{paragraphe.flatMap((l, j) => [...(j ? [<br key={`br${j}`} />] : []), ...enLigne(l, ctx, `${cle}-p${i}-${j}`)])}</p>);
  }
  return sortie;
}

/** Les pages que cite un volet, en vignettes : le papier reste sous les yeux, le long du fil. */
function Apercus({ pages, urlDePage, surPage }: { pages: number[] } & Contexte) {
  if (!pages.length) return null;
  return (
    <ul className="lf-volet-apercus" aria-label="Pages du papier">
      {pages.map((n) => {
        // eslint-disable-next-line @next/next/no-img-element
        const image = <img src={urlDePage(n)} alt={`Page ${n} du papier`} loading="lazy" />;
        return (
          <li key={n}>
            {surPage ? (
              <button type="button" onClick={() => surPage(n)} aria-label={`Voir la page ${n}`}>
                {image}
                <span>page {n}</span>
              </button>
            ) : (
              <span className="lf-volet-apercu">
                {image}
                <span>page {n}</span>
              </span>
            )}
          </li>
        );
      })}
    </ul>
  );
}

type Options = {
  /** Montrer, sous chaque volet, les vignettes des pages qu'il cite. */
  apercus?: boolean;
};

function pagesEnLettres(pages: number[]): string {
  return pages.length > 1 ? `pages ${pages[0]} à ${pages[pages.length - 1]}` : `page ${pages[0]}`;
}

/** Un volet rendu : son en-tête (type, date, établissement, pages), son contenu, et ses pages en vignettes. */
export function RenduDeVolet({ volet, urlDePage, surPage, entete, apercus }: { volet: Volet; entete?: ReactNode } & Contexte & Options) {
  return (
    <section className={`lf-volet lf-volet--${volet.type}`} aria-label={`${LIBELLES_DES_VOLETS[volet.type]}, ${dateEnLettres(volet.date)}`}>
      <header className="lf-volet-entete">
        <span className="lf-volet-type">{LIBELLES_DES_VOLETS[volet.type]}</span>
        <span className="lf-volet-date">{dateEnLettres(volet.date)}</span>
        {volet.etablissement && <span className="lf-volet-lieu">{volet.etablissement}</span>}
        {volet.pages.length > 0 && (
          surPage ? (
            <button type="button" className="lf-volet-pages" onClick={() => surPage(volet.pages[0])}>
              {pagesEnLettres(volet.pages)}
            </button>
          ) : (
            <span className="lf-volet-pages">{pagesEnLettres(volet.pages)}</span>
          )
        )}
        {entete}
      </header>
      <div className="lf-volet-corps">{blocs(volet.corps, { urlDePage, surPage }, `v${volet.rang}`)}</div>
      {apercus && <Apercus pages={volet.pages} urlDePage={urlDePage} surPage={surPage} />}
    </section>
  );
}

/**
 * Une Transcription entière, volets dans l'ordre donné. `variante="fil"` la montre comme un fil de vie :
 * une frise des dates à gauche, chaque volet avec son texte et ses images, les pages du papier en vignettes.
 * Le libellé patrimonial est dit par l'application.
 */
export function RenduDeTranscription({
  transcription,
  urlDePage,
  surPage,
  apercus,
  variante = "cartes",
}: { transcription: Transcription; variante?: "cartes" | "fil" } & Contexte & Options) {
  if (variante === "fil") {
    return (
      <ol className="lf-transcription lf-fil">
        {transcription.volets.map((v) => (
          <li key={v.rang} className="lf-fil-etape">
            <span className="lf-fil-repere" aria-hidden="true">
              <span className="lf-fil-point" />
              <span className="lf-fil-date">{v.date ? v.date.slice(0, 4) : "?"}</span>
            </span>
            <RenduDeVolet volet={v} urlDePage={urlDePage} surPage={surPage} apercus={apercus ?? true} />
          </li>
        ))}
      </ol>
    );
  }
  return (
    <div className="lf-transcription">
      {transcription.volets.map((v) => (
        <RenduDeVolet key={v.rang} volet={v} urlDePage={urlDePage} surPage={surPage} apercus={apercus} />
      ))}
    </div>
  );
}

/** La phrase qui accompagne toute Transcription montrée hors de la relecture (docs/specs/F6). */
export const MENTION_PATRIMONIALE =
  "Transcription d'un document ancien, relue par des agents de relecture. Ce n'est pas une donnée clinique vérifiée : en cas de doute, la page fait foi.";
