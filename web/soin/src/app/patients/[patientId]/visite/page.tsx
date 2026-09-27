import { Alert } from "@lafia/design";
import { connection } from "next/server";

import { Cadre, soignantConnecte } from "../../../../composants/Cadre";
import { FormulaireDeVisite } from "../../../../composants/FormulaireDeVisite";
import { domaine, soin } from "../../../../lib/soin";

type Parametres = { params: Promise<{ npi: string }>; searchParams: Promise<Record<string, string | undefined>> };

/** Nouvelle visite dans un cas : mesures, diagnostic, ordonnance ; puis le reçu à imprimer. */
export default async function NouvelleVisite({ params, searchParams }: Parametres) {
  await connection();
  const session = await soignantConnecte();
  const [{ npi }, { cas }] = await Promise.all([params, searchParams]);
  const [fiche, catalogue, hote] = await Promise.all([soin.fiche(npi), soin.catalogue(), domaine()]);
  const retour = { href: `/patients/${npi}`, libelle: "Retour à la fiche" };
  const leCas = fiche.corps?.cas.find((c) => c.id === cas);

  if (!fiche.corps || !catalogue.corps || !leCas) {
    return (
      <Cadre session={session} retour={retour}>
        <Alert tone="danger" title={leCas || !fiche.corps ? "Le service soin ne répond pas." : "Ce cas n’existe pas pour ce patient."} />
      </Cadre>
    );
  }
  if (leCas.statut !== "en-cours") {
    return (
      <Cadre session={session} retour={retour}>
        <Alert tone="attention" title="Ce cas est clos : ouvrez-en un nouveau depuis la fiche." />
      </Cadre>
    );
  }

  return (
    <Cadre session={session} retour={retour}>
      <FormulaireDeVisite
        npi={npi}
        patient={fiche.corps.patient}
        allergies={fiche.corps.allergies}
        cas={leCas}
        catalogue={catalogue.corps}
        role={session.role}
        adresseDuCarnet={`citoyen.${hote}`}
      />
    </Cadre>
  );
}
