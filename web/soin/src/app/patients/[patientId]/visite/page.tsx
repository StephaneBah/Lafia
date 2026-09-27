import { Alert, Button, Card, StatusBadge, TextInput, formatDate } from "@lafia/design";
import { redirect } from "next/navigation";
import { connection } from "next/server";

import { soignantConnecte } from "../../../../composants/Cadre";
import { EspacePatient, PatientIntrouvable } from "../../../../composants/EspacePatient";
import { FilDuCas } from "../../../../composants/FilDuCas";
import { FormulaireDeVisite } from "../../../../composants/FormulaireDeVisite";
import { adresseDuPatient } from "../../../../lib/adresses";
import { domaine, soin } from "../../../../lib/soin";
import type { Bandeau } from "../../../../lib/types";
import { ouvrirCas } from "../../../actions";

type Parametres = { params: Promise<{ patientId: string }>; searchParams: Promise<Record<string, string | undefined>> };

/** Sans cas choisi : continuer un cas en cours, ou en ouvrir un nouveau pour cette visite. */
function ChoixDuCas({ bandeau, erreur }: { bandeau: Bandeau; erreur?: string }) {
  const id = bandeau.patient.id;
  const enCours = bandeau.cas.filter((c) => c.statut === "en-cours");
  return (
    <div className="sn-choix">
      <Card className="sn-panneau">
        <h2 className="sn-h2">Dans quel cas ?</h2>
        {enCours.length === 0 ? (
          <div className="sn-vide">Aucun cas en cours : ouvrez-en un.</div>
        ) : (
          <ul className="sn-liste">
            {enCours.map((c) => (
              <li key={c.id} className="sn-cas">
                <div>
                  <div className="sn-cas-titre">{c.motif || "Cas d’un autre établissement"}</div>
                  <div className="sn-meta">{[c.debut && `Depuis le ${formatDate(c.debut)}`, c.etablissement].filter(Boolean).join(" · ")}</div>
                </div>
                <StatusBadge status="encours" size="pro" />
                <Button href={adresseDuPatient(id, `/visite?cas=${encodeURIComponent(c.id)}`)} size="pro" icon="heartbeat">
                  Nouvelle visite dans ce cas
                </Button>
              </li>
            ))}
          </ul>
        )}
      </Card>
      <Card className="sn-panneau">
        <h2 className="sn-h2">Ouvrir un cas</h2>
        {erreur === "motif" && <Alert tone="danger" title="Donnez un motif pour ouvrir le cas." />}
        <form action={ouvrirCas} className="lf-formulaire">
          <input type="hidden" name="patient_id" value={id} />
          <TextInput name="motif" label="Motif du cas" size="pro" placeholder="Fièvre et toux" required maxLength={200} />
          <Button type="submit" size="pro" icon="plus">
            Ouvrir le cas
          </Button>
        </form>
      </Card>
    </div>
  );
}

/**
 * Nouvelle visite. Sans cas choisi, on en choisit un ou on en ouvre un. Dans un cas, son historique
 * d'abord, puis le formulaire par étapes ; après l'enregistrement, le reçu à imprimer.
 */
export default async function NouvelleVisite({ params, searchParams }: Parametres) {
  await connection();
  const session = await soignantConnecte();
  const [{ patientId }, { cas, erreur }] = await Promise.all([params, searchParams]);
  const bandeau = await soin.bandeau(patientId);
  if (bandeau.statut !== 200 || !bandeau.corps) return <PatientIntrouvable session={session} statut={bandeau.statut} />;
  const relation = bandeau.corps.relation_de_soin;

  if (!cas) {
    if (!relation) redirect(adresseDuPatient(patientId));
    return (
      <EspacePatient session={session} bandeau={bandeau.corps} onglet="visite">
        <ChoixDuCas bandeau={bandeau.corps} erreur={erreur} />
      </EspacePatient>
    );
  }

  const leCas = bandeau.corps.cas.find((c) => c.id === cas);
  const [catalogue, dossier, hote] = await Promise.all([
    soin.catalogue(),
    relation ? soin.dossier(patientId) : Promise.resolve(null),
    domaine(),
  ]);
  const historique = dossier?.corps?.cas.find((c) => c.id === cas);

  let contenu;
  if (!leCas) contenu = <Alert tone="danger" title="Ce cas n’existe pas pour ce patient." />;
  else if (leCas.statut !== "en-cours")
    contenu = (
      <Alert tone="attention" title="Ce cas est clos : ouvrez-en un nouveau.">
        <a href={adresseDuPatient(patientId, "/visite")} className="sn-lien">
          Ouvrir un cas
        </a>
      </Alert>
    );
  else if (!catalogue.corps) contenu = <Alert tone="danger" title="Le service soin ne répond pas. Réessayez dans un instant." />;
  else
    contenu = (
      <div className="sn-colonne">
        <Card className="sn-panneau sn-historique">
          <h2 className="sn-h2">{`Historique du cas « ${leCas.motif || historique?.motif || "cas en cours"} »`}</h2>
          {historique ? (
            <FilDuCas cas={historique} produits={catalogue.corps.produits} />
          ) : (
            <p className="sn-meta">L’historique de ce cas s’affiche dès que votre visite l’a continué.</p>
          )}
        </Card>
        <FormulaireDeVisite
          patientId={patientId}
          patient={bandeau.corps.patient}
          allergies={bandeau.corps.allergies}
          cas={leCas}
          catalogue={catalogue.corps}
          role={session.role}
          adresseDuCarnet={`citoyen.${hote}`}
        />
      </div>
    );

  return (
    <EspacePatient session={session} bandeau={bandeau.corps} onglet={relation ? "visite" : undefined}>
      {contenu}
    </EspacePatient>
  );
}
