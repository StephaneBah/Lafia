import { Alert, Button, Card } from "@lafia/design";
import { connection } from "next/server";

import { Cadre, soignantConnecte } from "../../../../composants/Cadre";
import { Allergies, EnTetePatient } from "../../../../composants/Patient";
import { soin } from "../../../../lib/soin";
import { accesDUrgence } from "../../../actions";

type Parametres = { params: Promise<{ npi: string }>; searchParams: Promise<Record<string, string | undefined>> };

const MOTIFS = ["Patient inconscient", "Détresse vitale", "Hémorragie grave", "Autre motif (à préciser)"];

/** Accès d'urgence : un motif, une précision, puis le dossier ; tracé et visible par le patient. */
export default async function AccesDUrgence({ params, searchParams }: Parametres) {
  await connection();
  const session = await soignantConnecte();
  const [{ npi }, { erreur }] = await Promise.all([params, searchParams]);
  const fiche = await soin.fiche(npi);
  const retour = { href: `/patients/${npi}`, libelle: "Retour à la fiche" };

  return (
    <Cadre session={session} retour={retour}>
      <div className="sn-deux sn-deux--urgence">
        <Card className="sn-panneau">
          <Alert tone="urgence" title="Accès d’urgence vitale">
            L’accès est tracé et visible par le patient.
          </Alert>
          {erreur === "raison" && <Alert tone="danger" title="Choisissez un motif et précisez-le : dix caractères au moins." />}
          {erreur === "service" && <Alert tone="danger" title="Le service soin n’a pas ouvert l’accès. Réessayez." />}
          <form action={accesDUrgence} className="lf-formulaire">
            <input type="hidden" name="npi" value={npi} />
            <fieldset className="sn-fieldset">
              <legend className="lf-field-label">Motif</legend>
              <div className="sn-radios">
                {MOTIFS.map((motif, i) => (
                  <label key={motif} className="sn-radio">
                    <input type="radio" name="motif" value={motif} defaultChecked={i === 0} required />
                    {motif}
                  </label>
                ))}
              </div>
            </fieldset>
            <div className="lf-field lf-field--pro">
              <label className="lf-field-label" htmlFor="precision">
                Précision
              </label>
              <textarea id="precision" name="precision" className="sn-textarea" maxLength={400} placeholder="Amené par le SAMU, pas de proche présent." />
            </div>
            <Button type="submit" size="pro" variant="danger" icon="warning-octagon" block>
              Déclarer et ouvrir
            </Button>
          </form>
        </Card>
        {fiche.corps && (
          <div className="sn-vital">
            <EnTetePatient patient={fiche.corps.patient} npi={npi} />
            <Allergies allergies={fiche.corps.allergies} />
          </div>
        )}
      </div>
    </Cadre>
  );
}
