import { PageDeConnexion, type ParametresDePage } from "@lafia/commun";

import { ACTEUR, TITRE } from "../../libelles";

export default function Connexion({ searchParams }: ParametresDePage) {
  return <PageDeConnexion acteur={ACTEUR} titre={TITRE} searchParams={searchParams} />;
}
