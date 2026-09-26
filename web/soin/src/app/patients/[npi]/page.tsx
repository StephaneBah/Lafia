import { Alert, Button, Card, StatusBadge, TextInput, formatDate } from "@lafia/design";
import { connection } from "next/server";

import { Cadre, soignantConnecte } from "../../../composants/Cadre";
import { Allergies, EnTetePatient } from "../../../composants/Patient";
import { soin } from "../../../lib/soin";
import { ouvrirCas } from "../../actions";

type Parametres = { params: Promise<{ npi: string }>; searchParams: Promise<Record<string, string | undefined>> };

/** La fiche d'un patient trouvé par NPI : identité, allergies, cas. Rien de clinique avant la relation de soin. */
export default async function FicheDuPatient({ params, searchParams }: Parametres) {
  await connection();
  const session = await soignantConnecte();
  const [{ npi }, { erreur }] = await Promise.all([params, searchParams]);
  const reponse = await soin.fiche(npi);
  const retour = { href: "/", libelle: "Nouvelle recherche" };

  if (reponse.statut !== 200 || !reponse.corps) {
    return (
      <Cadre session={session} retour={retour}>
        <Alert
          tone={reponse.statut === 404 || reponse.statut === 422 ? "attention" : "danger"}
          title={reponse.statut === 404 || reponse.statut === 422 ? "Aucun patient pour ce NPI." : "Le service soin ne répond pas."}
        >
          Vérifiez les treize chiffres avec le patient, puis recherchez à nouveau.
        </Alert>
      </Cadre>
    );
  }
  const { patient, allergies, cas, relation_de_soin } = reponse.corps;
  const enCours = cas.filter((c) => c.statut === "en-cours");

  return (
    <Cadre session={session} retour={retour}>
      <Card className="sn-panneau sn-glisse">
        <EnTetePatient patient={patient} npi={npi}>
          {relation_de_soin && (
            <Button href={`/patients/${npi}/dossier`} size="pro" icon="eye">
              Ouvrir le dossier
            </Button>
          )}
        </EnTetePatient>
        <Allergies allergies={allergies} />
      </Card>

      {erreur && <Alert tone="danger" title="Le cas n’a pas été ouvert. Réessayez avec un motif." />}

      <div className="sn-deux">
        <Card className="sn-panneau">
          <h2 className="sn-h3">Cas de visite</h2>
          {cas.length === 0 && <div className="sn-vide">Aucun cas de visite pour ce patient.</div>}
          <ul className="sn-liste">
            {cas.map((c) => (
              <li key={c.id} className="sn-cas">
                <div>
                  <div className="sn-cas-titre">{c.motif}</div>
                  <div className="sn-meta">
                    {c.debut && `${formatDate(c.debut)} · `}
                    {c.etablissement}
                  </div>
                </div>
                <StatusBadge status={c.statut === "en-cours" ? "encours" : "termine"} size="pro" />
                {c.statut === "en-cours" && (
                  <Button href={`/patients/${npi}/visite?cas=${c.id}`} size="pro" variant={c.de_mon_etablissement ? "primary" : "secondary"} icon="heartbeat">
                    {`Continuer le cas « ${c.motif} »`}
                  </Button>
                )}
              </li>
            ))}
          </ul>
          {enCours.length > 0 && (
            <p className="sn-meta">Continuer un cas, le patient présent, ouvre le dossier : c’est la relation de soin.</p>
          )}
        </Card>

        <div className="sn-colonne">
          <Card className="sn-panneau">
            <h2 className="sn-h3">Ouvrir un nouveau cas</h2>
            <form action={ouvrirCas} className="lf-formulaire">
              <input type="hidden" name="npi" value={npi} />
              <TextInput name="motif" label="Motif du cas" size="pro" placeholder="Fièvre et toux" required maxLength={200} />
              <Button type="submit" size="pro" variant="secondary" icon="plus">
                Ouvrir un nouveau cas
              </Button>
            </form>
          </Card>
          {!relation_de_soin && (
            <Card className="sn-panneau sn-panneau--urgence">
              <h2 className="sn-h3">Urgence vitale</h2>
              <p className="sn-meta">Sans relation de soin, le dossier ne s’ouvre qu’avec une raison déclarée, tracée et visible par le patient.</p>
              <Button href={`/patients/${npi}/urgence`} size="pro" variant="danger" icon="warning-octagon">
                Accès d’urgence
              </Button>
            </Card>
          )}
        </div>
      </div>
    </Cadre>
  );
}
