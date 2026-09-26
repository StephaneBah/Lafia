// L'état du service citoyen et du noyau, replié en bas de l'accueil : utile au jury et au support,
// discret pour le citoyen.

const DELAI_MS = 5000;

type Sante = { statut: string; noyau: { statut: string; version_fhir: string | null } };

async function lireSante(): Promise<Sante | null> {
  const adresse = process.env.PASSERELLE_URL;
  if (!adresse) return null;
  try {
    const reponse = await fetch(`${adresse}/api/citoyen/sante`, { cache: "no-store", signal: AbortSignal.timeout(DELAI_MS) });
    if (![200, 503].includes(reponse.status)) return null;
    return (await reponse.json()) as Sante;
  } catch {
    return null;
  }
}

export async function EtatDuService({ connecte }: { connecte: boolean }) {
  const sante = await lireSante();
  const noyau = !sante
    ? "inconnu"
    : sante.noyau.statut === "disponible"
      ? `disponible, FHIR ${sante.noyau.version_fhir}`
      : sante.noyau.statut;
  return (
    <details className="carnet-service">
      <summary>État du service</summary>
      <dl>
        <dt>Service citoyen</dt>
        <dd>{sante?.statut ?? "injoignable"}</dd>
        <dt>Noyau</dt>
        <dd>{noyau}</dd>
        {connecte ? (
          <>
            <dt>Connecté comme</dt>
            <dd>citoyen</dd>
          </>
        ) : (
          <>
            <dt>Session</dt>
            <dd>aucune</dd>
          </>
        )}
      </dl>
    </details>
  );
}
