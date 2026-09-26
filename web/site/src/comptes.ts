// Comptes de démonstration montrés sur le site, un ou deux par application : repris de donnees/
// (agents.toml, officines.toml, citoyens.toml), où tous sont publics. Chaque page de connexion liste
// les autres, que identite lui donne. La suite (tests/test_site.py) vérifie qu'identite les connaît.

import type { Acteur, CompteAffiche } from "@lafia/design";

const MOT_DE_PASSE = "lafia-demo";

const agent = (identifiant: string): CompteAffiche => [
  { label: "Identifiant", value: identifiant },
  { label: "Mot de passe", value: MOT_DE_PASSE },
];

export const COMPTES_DU_SITE: Record<Acteur, { comptes: CompteAffiche[]; note: string }> = {
  citoyen: {
    comptes: [
      [
        { label: "NPI", value: "0000001204815" },
        { label: "Code carnet", value: "H3T-9QR" },
      ],
    ],
    note: "Le code carnet est imprimé sur le reçu de la dernière visite ; chaque nouvelle visite en donne un nouveau.",
  },
  soin: {
    comptes: [agent("medecin.cnhu.1"), agent("infirmier.cnhu")],
    note: "Médecin et infirmier au CNHU Hubert Koutoukou Maga, Cotonou.",
  },
  caisse: {
    comptes: [agent("caissier.cnhu")],
    note: "Caissière au CNHU Hubert Koutoukou Maga, Cotonou.",
  },
  pharmacie: {
    comptes: [agent("pharmacien.cnhu"), agent("officine.zogbo")],
    note: "Pharmacien du CNHU, et une officine de ville : la Pharmacie Baobab de Zogbo.",
  },
};
