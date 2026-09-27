import { Icon, type NomIcone } from "@lafia/design";

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
