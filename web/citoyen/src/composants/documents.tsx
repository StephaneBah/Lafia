import { Icon, type NomIcone } from "@lafia/design";
import {
  RenduDeTranscription,
  TYPES_DE_VOLET,
  lireTranscription,
  type TypeDeVolet,
  type Volet,
} from "@lafia/commun/transcription";

import type { MaTranscription, VoletLu } from "../lib/carnet";

// Le type d'un papier, en icône et en mot : on le reconnaît sans lire.

const ICONES_DES_TYPES: Record<string, NomIcone> = {
  carnet: "identification-card",
  "compte-rendu": "stethoscope",
  "resultat-analyse": "test-tube",
  ordonnance: "receipt",
  imagerie: "eye",
  certificat: "shield-check",
  autre: "copy",
};

export function IconeDuDocument({ type, size = 40 }: { type: string; size?: number }) {
  return <Icon name={ICONES_DES_TYPES[type] ?? "copy"} size={size} duotone />;
}

/** « 3 pages », « 1 page ». */
export function pages(n: number): string {
  return `${n} ${n > 1 ? "pages" : "page"}`;
}

/** La phrase qui accompagne tout texte relu dans le carnet : il recopie un papier, le papier fait foi. */
export const MENTION_DU_CARNET = "Ce texte recopie un ancien papier. Il a été relu, mais c'est le papier qui fait foi.";

export function MentionDuCarnet() {
  return (
    <p className="lf-mention-patrimoniale">
      <Icon name="info" size={22} />
      <span>{MENTION_DU_CARNET}</span>
    </p>
  );
}

/** « Papier abîmé à l'origine : … » : la note de l'agent quand le papier l'était avant d'être numérisé. */
export function PapierAbime({ note }: { note?: string | null }) {
  if (!note) return null;
  return (
    <small className="carnet-document-etat carnet-papier-abime">
      <Icon name="warning" size={18} />
      {`Papier abîmé à l’origine : ${note}`}
    </small>
  );
}

/** L'adresse d'une page d'un de mes documents, servie par l'application avec ma session. */
export function adresseDeLaPage(documentId: string, n: number): string {
  return `/documents/${encodeURIComponent(documentId)}/pages/${n}`;
}

/** Le texte relu d'un de mes documents, volet par volet, sous la phrase qui dit ce qu'il est. */
export function TexteRelu({ documentId, transcription }: { documentId: string; transcription: MaTranscription }) {
  return (
    <div className="carnet-texte-relu">
      <MentionDuCarnet />
      <RenduDeTranscription
        transcription={lireTranscription(transcription.markdown, transcription.pages)}
        urlDePage={(n) => adresseDeLaPage(documentId, n)}
        variante="fil"
      />
    </div>
  );
}

/** Un volet reçu du service, dans la forme que le rendu partagé attend. */
export function voletDe(v: VoletLu, rang: number, etablissement: string | null): Volet {
  const type = (TYPES_DE_VOLET as readonly string[]).includes(v.type) ? (v.type as TypeDeVolet) : "autre";
  return { titre: v.titre, type, date: v.date, etablissement, pages: v.pages, corps: v.corps, rang };
}
