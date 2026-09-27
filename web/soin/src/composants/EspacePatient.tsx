import { Alert, Button, Icon } from "@lafia/design";
import type { ReactNode } from "react";

import { adresseDuPatient } from "../lib/adresses";
import type { Bandeau, SessionSoignant } from "../lib/types";
import { Cadre } from "./Cadre";
import { BandeauPatient } from "./Patient";

export { adresseDuPatient };

export type Onglet = "synthese" | "cas" | "documents" | "visite";

const ONGLETS: { onglet: Onglet; libelle: string; suite: string; icone: "stethoscope" | "heartbeat" | "copy" | "plus" }[] = [
  { onglet: "synthese", libelle: "Synthèse", suite: "", icone: "stethoscope" },
  { onglet: "cas", libelle: "Cas", suite: "/cas", icone: "heartbeat" },
  { onglet: "documents", libelle: "Documents", suite: "/documents", icone: "copy" },
  { onglet: "visite", libelle: "Nouvelle visite", suite: "/visite", icone: "plus" },
];

/** Le soignant connecté, rappelé au-dessus du patient : qui lit ce dossier, et pour quel établissement. */
function Connecte({ session }: { session: SessionSoignant }) {
  return (
    <p className="sn-connecte">
      <Icon name="user" size={16} />
      <span>
        {`Connecté comme ${session.role} · `}
        <b>{session.nom}</b>
        {` · Établissement ${session.nom_etablissement}`}
      </span>
    </p>
  );
}

/**
 * L'espace patient : retour à la recherche, le soignant connecté, le bandeau patient persistant, puis
 * les onglets Synthèse, Cas, Documents et Nouvelle visite. Sans relation de soin, pas d'onglet : l'écran propose
 * d'ouvrir un cas, d'en continuer un ou de déclarer un accès d'urgence.
 */
export function EspacePatient({
  session,
  bandeau,
  onglet,
  children,
}: {
  session: SessionSoignant;
  bandeau: Bandeau;
  onglet?: Onglet;
  children: ReactNode;
}) {
  const id = bandeau.patient.id;
  return (
    <Cadre session={session}>
      <div className="sn-barre">
        <Button href="/" size="pro" variant="ghost" icon="magnifying-glass">
          Nouvelle recherche
        </Button>
        <span className="sn-espace" />
        <Connecte session={session} />
      </div>
      <BandeauPatient bandeau={bandeau} />
      {bandeau.relation_de_soin && onglet && (
        <nav className="sn-onglets" aria-label="Espace patient">
          {ONGLETS.map((o) => (
            <a
              key={o.onglet}
              href={adresseDuPatient(id, o.suite)}
              className="sn-onglet"
              aria-current={o.onglet === onglet ? "page" : undefined}
            >
              <Icon name={o.icone} size={20} />
              <span>{o.libelle}</span>
            </a>
          ))}
        </nav>
      )}
      <div className="sn-espace-contenu">{children}</div>
    </Cadre>
  );
}

/** Le patient n'a pas pu être chargé : l'écran le dit et ramène à la recherche. */
export function PatientIntrouvable({ session, statut }: { session: SessionSoignant; statut: number }) {
  const absent = statut === 404 || statut === 422;
  return (
    <Cadre session={session} retour={{ href: "/", libelle: "Nouvelle recherche" }}>
      <Alert tone={absent ? "attention" : "danger"} title={absent ? "Ce patient est introuvable." : "Le service soin ne répond pas."}>
        {absent ? "Recherchez-le à nouveau par son NPI." : "Réessayez dans un instant."}
      </Alert>
    </Cadre>
  );
}
