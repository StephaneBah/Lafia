import "../../caisse.css";

import { Alert, AppHeader, Button, formatFcfa } from "@lafia/design";
import { headers } from "next/headers";
import { redirect } from "next/navigation";
import { connection } from "next/server";

import { lireCaissier, lireRecepisse } from "../../../caisse";
import { Imprimer } from "./Imprimer";

type Parametres = { params: Promise<{ numero: string }> };

/** Date et heure du récépissé, à l'heure de Cotonou. */
function horodatage(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString("fr-FR", { timeZone: "Africa/Porto-Novo", dateStyle: "short", timeStyle: "short" });
}

/** Le récépissé d'un encaissement, à imprimer et à remettre au patient pour la pharmacie. */
export default async function PageDuRecepisse({ params }: Parametres) {
  await connection();
  const caissier = await lireCaissier();
  if (!caissier) redirect("/connexion");
  const { numero } = await params;
  const reponse = await lireRecepisse(decodeURIComponent(numero));
  const hote = ((await headers()).get("host") ?? "").replace(/:\d+$/, "");
  const site = `https://${hote.split(".").slice(1).join(".") || "localhost"}`;

  return (
    <>
      <AppHeader actor="caisse" actorLabel="Caisse" siteHref={site} place={caissier.nom_etablissement} user={caissier.nom} signOut />
      <main className="lf-app-main caisse-main caisse-main--recepisse">
        {reponse.ok ? (
          <>
            <Alert tone="succes" title={`Encaissé : ${formatFcfa(reponse.corps.montant)}`} className="caisse-ecran">
              Remettez le récépissé au patient : la pharmacie remet les lignes payées.
            </Alert>
            <article className="caisse-recepisse" aria-label="Récépissé">
              <div className="caisse-tampon caisse-tampon--recepisse" aria-hidden="true">
                Payé
              </div>
              <p className="caisse-recepisse-titre">{`Récépissé · ${reponse.corps.etablissement}`}</p>
              <p className="caisse-recepisse-numero">{reponse.corps.recepisse}</p>
              <p className="caisse-meta">{`Ordonnance ${reponse.corps.numero}`}</p>
              <ul className="caisse-recepisse-lignes">
                {reponse.corps.lignes.map((ligne) => (
                  <li key={ligne.id}>
                    <span>{ligne.libelle}</span>
                    <span className="caisse-chiffres">{formatFcfa(ligne.montant)}</span>
                  </li>
                ))}
              </ul>
              <p className="caisse-recepisse-total">
                <span>Payé</span>
                <span className="caisse-chiffres">{formatFcfa(reponse.corps.montant)}</span>
              </p>
              <p className="caisse-meta">{`${horodatage(reponse.corps.date)} · ${caissier.nom}`}</p>
            </article>
            <div className="caisse-actions caisse-ecran">
              <Imprimer />
              <Button href="/" variant="secondary" size="pro" icon="arrow-left">
                Encaisser une autre ordonnance
              </Button>
            </div>
          </>
        ) : (
          <>
            <Alert tone="attention" title="Aucun récépissé sous ce numéro, dans cet établissement." />
            <Button href="/" variant="secondary" size="pro" icon="arrow-left">
              Retour à la caisse
            </Button>
          </>
        )}
      </main>
    </>
  );
}
