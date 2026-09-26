import { Alert, Button, Card, StatusBadge, TimelineItem, formatDate } from "@lafia/design";
import { connection } from "next/server";

import { Cadre, soignantConnecte } from "../../../../composants/Cadre";
import { Allergies, EnTetePatient } from "../../../../composants/Patient";
import { soin } from "../../../../lib/soin";
import type { Visite } from "../../../../lib/types";
import { cloreCas, declarerAllergie } from "../../../actions";

/** Les classes ATC qu'une allergie déclarée couvre : la pharmacie arrête toute ligne de la classe. */
const CLASSES_D_ALLERGIE = [
  ["M01A", "AINS (ibuprofène, diclofénac)"],
  ["J01C", "Pénicillines (amoxicilline)"],
  ["J01E", "Sulfamides (cotrimoxazole)"],
  ["N02BE", "Paracétamol"],
  ["P01B", "Antipaludiques"],
];

type Parametres = { params: Promise<{ npi: string }>; searchParams: Promise<Record<string, string | undefined>> };

function icone(visite: Visite) {
  if (visite.urgence) return "warning-octagon" as const;
  if (visite.ordonnance) return "receipt" as const;
  if (visite.type === "soins-infirmiers") return "heartbeat" as const;
  return "stethoscope" as const;
}

/** Une visite sur le fil : mesures, diagnostics, ordonnance. */
function ContenuDeVisite({ visite }: { visite: Visite }) {
  return (
    <div className="sn-visite">
      {visite.motif && <p>{visite.motif}</p>}
      {visite.mesures.length > 0 && (
        <dl className="sn-kv">
          {visite.mesures.map((m) => (
            <div key={m.id}>
              <dt>{m.libelle}</dt>
              <dd>{`${m.valeur}${m.unite && m.unite !== "Cel" ? ` ${m.unite}` : m.unite === "Cel" ? " °C" : ""}`}</dd>
            </div>
          ))}
        </dl>
      )}
      {visite.diagnostics.map((d) => (
        <p key={d.id}>
          <b>{d.libelle}</b>
          {` · ${d.confirme ? "confirmé" : "provisoire"}`}
          {d.note && ` · ${d.note}`}
        </p>
      ))}
      {visite.ordonnance && (
        <div className="sn-ordonnance">
          <b className="lf-mono">{`Ordonnance ${visite.ordonnance.numero ?? ""}`}</b>
          <ul>
            {visite.ordonnance.lignes.map((l) => (
              <li key={l.id}>
                {l.libelle}
                {l.posologie && <span className="sn-meta">{` · ${l.posologie}`}</span>}
                {l.quantite !== null && <span className="sn-meta">{` · qté ${l.quantite}`}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

/** Le dossier, cas par cas sur le fil. Le médecin clôt un cas en cours. */
export default async function DossierDuPatient({ params, searchParams }: Parametres) {
  await connection();
  const session = await soignantConnecte();
  const [{ npi }, recherche] = await Promise.all([params, searchParams]);
  const reponse = await soin.dossier(npi);
  const retour = { href: `/patients/${npi}`, libelle: "Retour à la fiche" };

  if (reponse.statut !== 200 || !reponse.corps) {
    return (
      <Cadre session={session} retour={retour}>
        {reponse.statut === 403 ? (
          <Alert tone="attention" title="Pas de relation de soin avec ce patient.">
            Continuez ou ouvrez un cas depuis la fiche, le patient présent. En urgence vitale seulement, déclarez un accès d’urgence.
          </Alert>
        ) : (
          <Alert tone="danger" title="Le service soin ne répond pas." />
        )}
      </Cadre>
    );
  }
  const { patient, allergies, cas } = reponse.corps;
  const medecin = session.role === "médecin";

  return (
    <Cadre session={session} retour={retour}>
      {recherche.urgence && (
        <Alert tone="urgence" title="Accès d’urgence ouvert">
          L’accès est tracé avec sa raison, et le patient le verra dans son carnet.
        </Alert>
      )}
      {recherche.clos && <Alert tone="succes" title="Cas clos." />}
      {recherche.erreur && <Alert tone="danger" title="L’action n’a pas abouti. Réessayez." />}
      <Card className="sn-panneau">
        <EnTetePatient patient={patient} npi={npi} />
      </Card>
      <div className="sn-dossier">
        <Card className="sn-panneau">
          <h2 className="sn-h3">D’abord</h2>
          <Allergies allergies={allergies} />
          <form action={declarerAllergie} className="lf-formulaire">
            <input type="hidden" name="npi" value={npi} />
            <div className="lf-field lf-field--pro">
              <label className="lf-field-label" htmlFor="allergie">
                Déclarer une allergie
              </label>
              <select id="allergie" name="allergie" className="lf-input sn-select" required defaultValue="">
                <option value="" disabled>
                  Classe de médicaments
                </option>
                {CLASSES_D_ALLERGIE.map(([code, libelle]) => (
                  <option key={code} value={`${code}|${libelle}`}>
                    {libelle}
                  </option>
                ))}
              </select>
            </div>
            <Button type="submit" size="pro" variant="secondary" icon="plus">
              Déclarer
            </Button>
          </form>
        </Card>
        <div className="sn-colonne">
          {cas.length === 0 && <div className="sn-vide">Aucun cas de visite.</div>}
          {cas.map((c) => (
            <Card key={c.id} className="sn-panneau">
              <div className="sn-cas-tete">
                <h2 className="sn-h3">{`Cas de visite · ${c.motif}`}</h2>
                <StatusBadge status={c.statut === "en-cours" ? "encours" : "termine"} size="pro" />
                <span className="sn-espace" />
                {c.statut === "en-cours" && (
                  <>
                    <Button href={`/patients/${npi}/visite?cas=${c.id}`} size="pro" icon="plus">
                      Nouvelle visite
                    </Button>
                    {medecin && (
                      <form action={cloreCas}>
                        <input type="hidden" name="npi" value={npi} />
                        <input type="hidden" name="cas" value={c.id} />
                        <Button type="submit" size="pro" variant="secondary" icon="check">
                          Clore le cas
                        </Button>
                      </form>
                    )}
                  </>
                )}
              </div>
              <p className="sn-meta">
                {`Ouvert ${c.debut ? `le ${formatDate(c.debut)} ` : ""}à ${c.etablissement}`}
                {c.fin && ` · clos le ${formatDate(c.fin)}`}
              </p>
              {c.visites.length === 0 ? (
                <div className="sn-vide">Aucune visite encore dans ce cas.</div>
              ) : (
                <ol className="lf-timeline">
                  {c.visites.map((v, i) => (
                    <TimelineItem
                      key={v.id}
                      first={i === 0}
                      last={i === c.visites.length - 1}
                      state={c.statut === "en-cours" && i === c.visites.length - 1 ? "current" : "done"}
                      icon={icone(v)}
                      date={v.date ? formatDate(v.date) : undefined}
                      place={[v.etablissement, v.soignant].filter(Boolean).join(" · ")}
                      title={v.type_libelle}
                      animate
                      index={i}
                    >
                      <ContenuDeVisite visite={v} />
                    </TimelineItem>
                  ))}
                </ol>
              )}
            </Card>
          ))}
        </div>
      </div>
    </Cadre>
  );
}
