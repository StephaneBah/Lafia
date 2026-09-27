import { Icon, formatDate, type NomIcone } from "@lafia/design";

import { adresseDuPatient } from "../lib/adresses";
import { LIBELLES_DES_ORIGINES, type DocumentDuDossier, type Origine } from "../lib/types";

// Les Documents du dossier (ADR 0008) et l'origine de chaque entrée (ADR 0007) : icône et mot,
// jamais la couleur seule.

const ICONES_DES_TYPES: Record<string, NomIcone> = {
  carnet: "identification-card",
  "compte-rendu": "stethoscope",
  "resultat-analyse": "test-tube",
  ordonnance: "receipt",
  imagerie: "eye",
  certificat: "shield-check",
  autre: "copy",
};

const ICONES_DES_ORIGINES: Record<Origine, NomIcone> = {
  visite: "stethoscope",
  numerisation: "eye",
  declaration: "user",
  report: "copy",
};

/** D'où vient une entrée : « Déclaré par le patient », « Reporté depuis un document », « Relevé en visite ». */
export function OrigineDeLEntree({ origine }: { origine?: Origine | null }) {
  if (!origine) return null;
  return (
    <span className="sn-origine">
      <Icon name={ICONES_DES_ORIGINES[origine]} size={16} />
      {LIBELLES_DES_ORIGINES[origine]}
    </span>
  );
}

/** Un papier numérisé n'a été vérifié par personne : le badge le dit sur chaque Document. */
export function NonVerifie() {
  return (
    <span className="lf-badge lf-badge--pro lf-tone-apayer">
      <Icon name="warning" size={16} />
      <span>Numérisé, non vérifié</span>
    </span>
  );
}

export function IconeDuType({ type, size = 24 }: { type: string; size?: number }) {
  return <Icon name={ICONES_DES_TYPES[type] ?? "copy"} size={size} />;
}

function details(d: DocumentDuDossier): string {
  return [
    d.annee,
    d.etablissement,
    `${d.pages} page${d.pages > 1 ? "s" : ""}`,
    d.depose_le && `ajouté le ${formatDate(d.depose_le)}`,
  ]
    .filter(Boolean)
    .join(" · ");
}

/** La liste des Documents : type (icône et mot), année, établissement d'origine, pages, lisibilité. */
export function ListeDesDocuments({
  patientId,
  documents,
  choisi,
}: {
  patientId: string;
  documents: DocumentDuDossier[];
  choisi?: string;
}) {
  if (documents.length === 0) {
    return <div className="sn-vide">Aucun document au dossier. Ajoutez les papiers que le patient a apportés.</div>;
  }
  return (
    <ul className="sn-liste">
      {documents.map((d) => (
        <li key={d.id}>
          <a
            href={adresseDuPatient(patientId, `/documents?document=${encodeURIComponent(d.id)}`)}
            className="sn-document"
            aria-current={d.id === choisi ? "true" : undefined}
          >
            <IconeDuType type={d.type} />
            <span>
              <b>{d.libelle}</b>
              <span className="sn-meta sn-bloc">{details(d)}</span>
              <span className="sn-document-etats">
                <NonVerifie />
                {d.lisibilite === "partiel" ? (
                  <span className="sn-origine">
                    <Icon name="warning" size={16} />
                    Partiellement lisible
                  </span>
                ) : (
                  <span className="sn-origine">
                    <Icon name="check" size={16} />
                    Lisible
                  </span>
                )}
              </span>
            </span>
          </a>
        </li>
      ))}
    </ul>
  );
}

/**
 * Les pages d'un Document : une image s'affiche ici, un PDF s'ouvre dans un nouvel onglet. Les octets
 * passent par l'application, qui les lit au service soin avec la session du soignant.
 */
export function Visionneuse({ document, page }: { document: DocumentDuDossier; page: number }) {
  const rang = Math.min(Math.max(page, 1), Math.max(document.pages, 1));
  const format = document.formats?.[rang - 1] ?? "image/jpeg";
  const source = `/documents/${encodeURIComponent(document.id)}/pages/${rang}`;
  const vers = (n: number) => `?document=${encodeURIComponent(document.id)}&page=${n}`;
  return (
    <div className="sn-visionneuse">
      <nav className="sn-pages" aria-label="Pages du document">
        {Array.from({ length: document.pages }, (_, i) => i + 1).map((n) => (
          <a key={n} href={vers(n)} className="sn-page" aria-current={n === rang ? "page" : undefined}>
            {`Page ${n}`}
          </a>
        ))}
      </nav>
      {format === "application/pdf" ? (
        <p className="sn-intro">
          <Icon name="arrow-square-out" size={20} />
          <a href={source} target="_blank" rel="noopener" className="sn-lien">
            {`Ouvrir la page ${rang} (PDF) dans un nouvel onglet`}
          </a>
        </p>
      ) : (
        // Les octets viennent de l'application elle-même, par la session : pas d'optimisation d'image.
        // eslint-disable-next-line @next/next/no-img-element
        <img src={source} alt={`${document.libelle}, page ${rang} sur ${document.pages}`} className="sn-page-image" />
      )}
      <p className="sn-meta">
        <a href={source} target="_blank" rel="noopener" className="sn-lien">
          Ouvrir en grand
        </a>
      </p>
    </div>
  );
}
