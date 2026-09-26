import { PageDeConnexion, type ParametresDePage } from "@lafia/commun";

export default function Connexion({ searchParams }: ParametresDePage) {
  return <PageDeConnexion acteur="pharmacie" titre="Pharmacie" searchParams={searchParams} />;
}
