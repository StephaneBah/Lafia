import { connection } from "next/server";

import { agentOuAccueil, Bureau } from "../../../Bureau";
import { depotOuRefus, type ParametresDuDepot } from "../depot";
import { Numeriser } from "./Numeriser";

/** Étape 3 : numériser un document du patient, dans son dépôt encore ouvert. */
export default async function NumeriserUnDocument({ params }: ParametresDuDepot) {
  await connection();
  const agent = await agentOuAccueil();
  const { id } = await params;
  const lu = await depotOuRefus(id, `/depots/${encodeURIComponent(id)}/numeriser`);

  return (
    <Bureau agent={agent} etape={3} titre="Numériser un document">
      {"refus" in lu ? (
        lu.refus
      ) : (
        <>
          <p className="num-meta">
            {`Pour ${lu.depot.patient.prenoms} ${lu.depot.patient.nom} · année de naissance ${lu.depot.patient.annee_de_naissance}`}
          </p>
          <Numeriser depot={id} anneeCourante={new Date().getFullYear()} />
        </>
      )}
    </Bureau>
  );
}
