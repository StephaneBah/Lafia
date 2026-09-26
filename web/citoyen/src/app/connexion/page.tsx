import { Alert, Button, CodeField, DemoAccount, NpiField, formatNpi } from "@lafia/design";
import { Illustration } from "@lafia/design/illustration";
import { connection } from "next/server";

import { Cadre } from "../../composants/cadre";

/** Ce que la page dit de chaque refus que rend identite (`/connexion?erreur=…`). */
const MESSAGES_DE_REFUS: Record<string, string> = {
  identifiants: "NPI ou code carnet incorrect. Regardez le code en bas de votre dernier reçu.",
  application: "Ce compte n'ouvre pas le carnet.",
  verrouille: "Trop d'essais : réessayez dans 15 minutes.",
};

type CitoyenDeDemonstration = { npi: string; code: string; role: "citoyen" };

/** Les citoyens de démonstration, que identite liste pour l'application citoyen (codes publics). */
async function citoyensDeDemonstration(): Promise<CitoyenDeDemonstration[]> {
  const adresse = process.env.PASSERELLE_URL;
  if (!adresse) return [];
  try {
    const reponse = await fetch(`${adresse}/api/identite/comptes-de-demonstration`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
    if (!reponse.ok) return [];
    const comptes = (await reponse.json()) as Array<Partial<CitoyenDeDemonstration>>;
    return comptes.filter((c): c is CitoyenDeDemonstration => typeof c.npi === "string" && typeof c.code === "string");
  } catch {
    return [];
  }
}

export default async function Connexion({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  await connection();
  const [{ erreur }, citoyens] = await Promise.all([searchParams, citoyensDeDemonstration()]);
  const message = typeof erreur === "string" ? MESSAGES_DE_REFUS[erreur] : undefined;

  return (
    <Cadre connecte={false}>
      <h1 className="carnet-titre">Ouvrir mon carnet</h1>
      <div className="carnet-illu-connexion">
        <Illustration name="citoyen-connexion" label="Votre NPI et le code carnet imprimé en bas de votre reçu ouvrent votre carnet." />
      </div>
      {message && <Alert tone="danger" title={message} />}
      {/* Le formulaire va droit à identite : l'application ne voit jamais le code, ni le jeton posé en retour. */}
      <form className="carnet-formulaire" method="post" action="/api/identite/citoyen/connexion">
        <NpiField name="npi" label="Mon NPI" hint="Le numéro de ma carte d'identité." size="citizen" required autoFocus />
        <CodeField name="code" label="Code carnet" hint="Imprimé en bas de mon reçu, dans le cadre." size="citizen" required />
        <Button type="submit" icon="lock-simple" size="citizen" block>
          Ouvrir mon carnet
        </Button>
      </form>
      {citoyens.length > 0 && (
        <DemoAccount
          comptes={citoyens.map((c) => [
            { label: "NPI", value: formatNpi(c.npi) },
            { label: "Code carnet", value: c.code },
          ])}
          note="Codes publics : toutes les données sont fictives. Le premier carnet a des soins et un traitement en cours, le deuxième une ordonnance à payer, le troisième est vide."
        />
      )}
    </Cadre>
  );
}
