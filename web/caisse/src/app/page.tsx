import "./caisse.css";

import { EtatDeLActeur } from "@lafia/commun";
import { Alert, AppHeader, Button, TextInput } from "@lafia/design";
import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { connection } from "next/server";

import { lireCaissier, lireOrdonnance, type Caissier } from "../caisse";
import { Encaissement } from "./Encaissement";

type Parametres = { searchParams: Promise<Record<string, string | string[] | undefined>> };

/** Ce que l'accueil dit d'un encaissement refusé (`actions.ts`). */
const REFUS: Record<string, { titre: string; texte?: string }> = {
  "deja-payee": {
    titre: "Une ligne vient d'être payée.",
    texte: "Rien n'a été encaissé. Les lignes déjà payées sont marquées : cochez celles qui restent.",
  },
  "aucune-ligne": { titre: "Aucune ligne cochée.", texte: "Cochez au moins une ligne à encaisser." },
  introuvable: { titre: "Ordonnance introuvable." },
  service: { titre: "Le service caisse ne répond pas.", texte: "Rien n'a été encaissé. Réessayez dans un instant." },
};

async function adresseDuSite(): Promise<string> {
  const hote = ((await headers()).get("host") ?? "").replace(/:\d+$/, "");
  return `https://${hote.split(".").slice(1).join(".") || "localhost"}`;
}

/** Qui est connecté : rôle, nom et établissement, lus par identite. */
function Session({ caissier }: { caissier: Caissier }) {
  return (
    <dl className="caisse-session">
      <dt>Connecté comme</dt>
      <dd>{caissier.role}</dd>
      <dt>Nom</dt>
      <dd>{caissier.nom}</dd>
      <dt>Établissement</dt>
      <dd>{caissier.nom_etablissement}</dd>
    </dl>
  );
}

/** Ce que la caisse montre du numéro tapé : l'ordonnance à encaisser, ou pourquoi elle ne s'ouvre pas. */
async function OrdonnanceOuverte({ numero }: { numero: string }) {
  const reponse = await lireOrdonnance(numero);
  if (reponse.ok) return <Encaissement ordonnance={reponse.corps} />;
  if (reponse.statut === 401 || reponse.statut === 403) redirect("/connexion");
  if (reponse.statut === 404) {
    return (
      <Alert tone="attention" title="Aucune ordonnance à payer sous ce numéro, dans cet établissement.">
        Vérifiez le numéro sur le reçu du patient : trois lettres ORD, puis six caractères.
      </Alert>
    );
  }
  return <Alert tone="danger" title="Le service caisse ne répond pas." />;
}

/**
 * L'accueil de la caisse. Sans session : l'état du service et « Se connecter ». Avec : le numéro
 * d'ordonnance à taper ou scanner, puis l'ordonnance tarifée à encaisser.
 */
export default async function Accueil({ searchParams }: Parametres) {
  await connection();
  const caissier = await lireCaissier();
  if (!caissier) return <EtatDeLActeur titre="Caisse" service="caisse" avecConnexion />;

  const { numero: brut, erreur } = await searchParams;
  const numero = typeof brut === "string" ? brut.trim() : "";
  const refus = typeof erreur === "string" ? REFUS[erreur] : undefined;

  return (
    <>
      <AppHeader
        actor="caisse"
        actorLabel="Caisse"
        siteHref={await adresseDuSite()}
        place={caissier.nom_etablissement}
        user={caissier.nom}
        signOut
      />
      <main className="lf-app-main caisse-main">
        <div className="caisse-entete">
          <h1 className="lf-app-titre">Encaisser une ordonnance</h1>
          <Session caissier={caissier} />
        </div>
        <form className="caisse-recherche" method="get" action="/">
          <TextInput
            label="Numéro d'ordonnance"
            name="numero"
            defaultValue={numero}
            icon="receipt"
            size="pro"
            className="caisse-champ-numero"
            placeholder="ORD-7K4-M2P"
            autoComplete="off"
            autoCapitalize="characters"
            spellCheck={false}
            autoFocus={!numero}
            required
          />
          <Button type="submit" size="pro" icon="magnifying-glass">
            Ouvrir
          </Button>
          <span className="caisse-meta">ou scannez le QR code du reçu</span>
        </form>
        {refus && (
          <Alert tone={erreur === "service" ? "danger" : "attention"} title={refus.titre}>
            {refus.texte}
          </Alert>
        )}
        {numero && <OrdonnanceOuverte numero={numero} />}
      </main>
    </>
  );
}
