import { Alert, Button, Card, StatusBadge, formatDate } from "@lafia/design";
import { redirect } from "next/navigation";
import { connection } from "next/server";

import { soignantConnecte } from "../../../../composants/Cadre";
import { EspacePatient, PatientIntrouvable } from "../../../../composants/EspacePatient";
import { FilDuCas } from "../../../../composants/FilDuCas";
import { adresseDuPatient } from "../../../../lib/adresses";
import { soin } from "../../../../lib/soin";
import type { Cas, Produit, SessionSoignant } from "../../../../lib/types";
import { cloreCas } from "../../../actions";

type Parametres = { params: Promise<{ patientId: string }>; searchParams: Promise<Record<string, string | undefined>> };

const MESSAGES: Record<string, { ton: "succes" | "danger"; titre: string }> = {
  clos: { ton: "succes", titre: "Cas clos. Il reste dans l’historique du patient." },
  "cloture-relation": { ton: "danger", titre: "Seul un établissement qui suit ce cas peut le clore." },
  cloture: { ton: "danger", titre: "Le cas n’a pas été clos. Réessayez." },
};

function periode(cas: Cas): string {
  return [
    cas.debut && `Ouvert le ${formatDate(cas.debut)}`,
    cas.fin && `clos le ${formatDate(cas.fin)}`,
    cas.etablissement,
    `${cas.visites.length} visite${cas.visites.length > 1 ? "s" : ""}`,
  ]
    .filter(Boolean)
    .join(" · ");
}

/** Un cas : son titre, son fil de visites, et ce qu'on peut y faire tant qu'il est en cours. */
function CarteDuCas({
  cas,
  patientId,
  session,
  produits,
}: {
  cas: Cas;
  patientId: string;
  session: SessionSoignant;
  produits: Produit[];
}) {
  const enCours = cas.statut === "en-cours";
  return (
    <Card className="sn-panneau">
      <div className="sn-cas-tete">
        <h2 className="sn-h2">{cas.motif || "Cas"}</h2>
        <StatusBadge status={enCours ? "encours" : "termine"} size="pro" />
      </div>
      <p className="sn-meta">{periode(cas)}</p>
      <FilDuCas cas={cas} produits={produits} />
      {enCours && (
        <div className="sn-actions">
          <Button href={adresseDuPatient(patientId, `/visite?cas=${encodeURIComponent(cas.id)}`)} size="pro" icon="plus">
            Nouvelle visite dans ce cas
          </Button>
          {session.role === "médecin" && (
            <form action={cloreCas}>
              <input type="hidden" name="patient_id" value={patientId} />
              <input type="hidden" name="cas" value={cas.id} />
              <Button type="submit" size="pro" variant="secondary" icon="check">
                Clore le cas
              </Button>
            </form>
          )}
        </div>
      )}
    </Card>
  );
}

/**
 * L'onglet Cas : l'historique du patient, cas par cas. Le cas qu'on vient de choisir d'abord, déplié,
 * puis les cas en cours, puis les cas clos, repliés.
 */
export default async function CasDuPatient({ params, searchParams }: Parametres) {
  await connection();
  const session = await soignantConnecte();
  const [{ patientId }, recherche] = await Promise.all([params, searchParams]);
  const bandeau = await soin.bandeau(patientId);
  if (bandeau.statut !== 200 || !bandeau.corps) return <PatientIntrouvable session={session} statut={bandeau.statut} />;
  if (!bandeau.corps.relation_de_soin) redirect(adresseDuPatient(patientId));

  const [dossier, catalogue] = await Promise.all([soin.dossier(patientId), soin.catalogue()]);
  if (dossier.statut === 403) redirect(adresseDuPatient(patientId));
  const produits = catalogue.corps?.produits ?? [];
  const tous = [...(dossier.corps?.cas ?? [])].sort((a, b) => {
    if (a.statut !== b.statut) return a.statut === "en-cours" ? -1 : 1;
    return (b.debut ?? "").localeCompare(a.debut ?? "");
  });
  const choisi = tous.find((c) => c.id === recherche.cas) ?? tous.find((c) => c.statut === "en-cours");
  const autres = tous.filter((c) => c !== choisi);
  const message = recherche.clos ? MESSAGES.clos : recherche.erreur ? MESSAGES[recherche.erreur] : undefined;

  return (
    <EspacePatient session={session} bandeau={bandeau.corps} onglet="cas">
      {message && <Alert tone={message.ton} title={message.titre} />}
      {!dossier.corps ? (
        <Alert tone="danger" title="Le service soin ne répond pas. Réessayez dans un instant." />
      ) : tous.length === 0 ? (
        <div className="sn-vide">
          Aucun cas encore.{" "}
          <a href={adresseDuPatient(patientId, "/visite")} className="sn-lien">
            Ouvrir un cas
          </a>
        </div>
      ) : (
        <div className="sn-colonne">
          {choisi && <CarteDuCas cas={choisi} patientId={patientId} session={session} produits={produits} />}
          {autres.length > 0 && (
            <section className="sn-colonne" aria-label="Autres cas">
              <h2 className="sn-h3">{choisi ? "Autres cas" : "Cas"}</h2>
              {autres.map((c) => (
                <details key={c.id} className="sn-details sn-details--cas">
                  <summary>
                    <span className="sn-cas-titre">{c.motif || "Cas"}</span>
                    <StatusBadge status={c.statut === "en-cours" ? "encours" : "termine"} size="pro" />
                    <span className="sn-meta">{periode(c)}</span>
                  </summary>
                  <CarteDuCas cas={c} patientId={patientId} session={session} produits={produits} />
                </details>
              ))}
            </section>
          )}
        </div>
      )}
    </EspacePatient>
  );
}
